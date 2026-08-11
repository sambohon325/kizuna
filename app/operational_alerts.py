from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.email_delivery import send_email, smtp_ready
from app.models import OperationalAlertDelivery
from app.observability import log_event, service_logger


SEVERITY = {"warning": 1, "error": 2}
logger = service_logger("operations-alerts")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _masked_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "configured email"
    return f"{local[:1]}***@{domain}"


def configured_channels() -> list[dict]:
    channels = []
    if settings.operations_alert_email:
        channels.append({"key": "email", "ready": smtp_ready(), "target_hint": _masked_email(settings.operations_alert_email)})
    if settings.operations_alert_webhook_url:
        parsed = urlparse(settings.operations_alert_webhook_url)
        allowed_scheme = parsed.scheme == "https" or (settings.environment.casefold() != "production" and parsed.scheme == "http")
        channels.append({"key": "webhook", "ready": allowed_scheme and bool(parsed.hostname), "target_hint": parsed.hostname or "configured webhook"})
    return channels


def _fingerprint(alert: dict) -> str:
    stable = {"key": alert.get("key"), "severity": alert.get("severity"), "message": alert.get("message"), "action": alert.get("action")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _payload(alert: dict, *, test: bool) -> dict:
    label = "TEST" if test else alert.get("severity", "warning").upper()
    title = f"Kizuna operations {label}: {alert.get('title', 'Studio notice')}"
    text = f"{title}\n\n{alert.get('message', '')}\n\nRecommended action: {alert.get('action', '')}\n\nStudio: {settings.public_url}"
    return {
        "event": "kizuna.operations.alert.test" if test else "kizuna.operations.alert",
        "title": title,
        "text": text,
        "content": text,
        "severity": alert.get("severity", "warning"),
        "alert_key": alert.get("key", "test"),
        "message": alert.get("message", ""),
        "action": alert.get("action", ""),
        "studio_url": settings.public_url,
        "sent_at": utcnow().isoformat() + "Z",
    }


def _send_webhook(payload: dict) -> int:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "Kizuna-Operations/1.0"}
    if settings.operations_alert_webhook_secret:
        digest = hmac.new(settings.operations_alert_webhook_secret.encode(), encoded, hashlib.sha256).hexdigest()
        headers["X-Kizuna-Signature"] = f"sha256={digest}"
    request = urllib.request.Request(settings.operations_alert_webhook_url, data=encoded, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Webhook returned HTTP {response.status}")
        return response.status


def _recently_attempted(db: Session, channel: str, fingerprint: str, now: datetime) -> bool:
    latest = db.scalar(select(OperationalAlertDelivery).where(OperationalAlertDelivery.channel == channel, OperationalAlertDelivery.fingerprint == fingerprint).order_by(OperationalAlertDelivery.created_at.desc(), OperationalAlertDelivery.id.desc()))
    if latest is None:
        return False
    if latest.status == "delivered" and latest.delivered_at:
        return latest.delivered_at >= now - timedelta(minutes=max(1, settings.operations_alert_cooldown_minutes))
    return latest.created_at >= now - timedelta(minutes=max(1, settings.operations_alert_retry_minutes))


def dispatch_operational_alerts(db: Session, readiness: dict, *, force: bool = False, test: bool = False) -> dict:
    now = utcnow()
    cutoff = now - timedelta(days=max(1, settings.operations_alert_retention_days))
    db.execute(delete(OperationalAlertDelivery).where(OperationalAlertDelivery.created_at < cutoff))
    channels = configured_channels()
    if not channels:
        return {"configured": False, "attempted": 0, "delivered": 0, "failed": 0, "skipped": 0}
    if test:
        alerts = [{"key": f"test-{uuid4().hex}", "severity": "warning", "title": "Test alert", "message": "Kizuna can reach this external operations channel.", "action": "No action is required; this was a requested delivery test."}]
    else:
        threshold = SEVERITY.get(settings.operations_alert_min_severity.casefold(), 2)
        alerts = [alert for alert in readiness.get("alerts", []) if SEVERITY.get(alert.get("severity", "warning"), 1) >= threshold]
    result = {"configured": True, "attempted": 0, "delivered": 0, "failed": 0, "skipped": 0}
    for alert in alerts:
        fingerprint = _fingerprint(alert)
        payload = _payload(alert, test=test)
        for channel in channels:
            if not force and _recently_attempted(db, channel["key"], fingerprint, now):
                result["skipped"] += 1
                continue
            item = OperationalAlertDelivery(channel=channel["key"], alert_key=alert.get("key", "operations"), fingerprint=fingerprint, severity=alert.get("severity", "warning"), target_hint=channel["target_hint"], payload={key: payload[key] for key in ("event", "title", "severity", "alert_key", "message", "action", "sent_at")})
            db.add(item)
            db.flush()
            result["attempted"] += 1
            try:
                if not channel["ready"]:
                    raise RuntimeError(f"The {channel['key']} alert channel is not fully configured")
                if channel["key"] == "email":
                    send_email(settings.operations_alert_email, payload["title"], payload["text"])
                    item.response_code = 250
                else:
                    item.response_code = _send_webhook(payload)
                item.status = "delivered"
                item.delivered_at = utcnow()
                result["delivered"] += 1
                log_event(logger, logging.INFO, "operational_alert_delivered", "An external operational alert was delivered", channel=channel["key"], alert_key=item.alert_key, severity=item.severity, response_code=item.response_code)
            except Exception as exc:
                item.status = "failed"
                code = getattr(exc, "code", None) or getattr(exc, "smtp_code", None)
                item.response_code = int(code) if isinstance(code, int) else item.response_code
                item.error = f"{type(exc).__name__}{f' ({code})' if code is not None else ''}"
                result["failed"] += 1
                log_event(logger, logging.WARNING, "operational_alert_failed", "An external operational alert could not be delivered", channel=channel["key"], alert_key=item.alert_key, severity=item.severity, error_type=type(exc).__name__, response_code=item.response_code)
            db.flush()
    return result


def alert_delivery_status(db: Session) -> dict:
    channels = configured_channels()
    latest = db.scalars(select(OperationalAlertDelivery).order_by(OperationalAlertDelivery.created_at.desc(), OperationalAlertDelivery.id.desc()).limit(10)).all()
    return {
        "configured": bool(channels),
        "channels": channels,
        "minimum_severity": settings.operations_alert_min_severity.casefold(),
        "cooldown_minutes": settings.operations_alert_cooldown_minutes,
        "history": [{"id": item.id, "channel": item.channel, "alert_key": item.alert_key, "severity": item.severity, "status": item.status, "target_hint": item.target_hint, "response_code": item.response_code, "error": bool(item.error), "delivered_at": item.delivered_at.isoformat() + "Z" if item.delivered_at else "", "created_at": item.created_at.isoformat() + "Z"} for item in latest],
    }
