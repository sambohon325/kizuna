from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import ServiceHeartbeat


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "service": getattr(record, "service", record.name),
            "event": getattr(record, "event", "message"),
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", {})
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def service_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(f"kizuna.{service}")
    if not any(getattr(handler, "kizuna_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler.kizuna_json = True
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: int, event: str, message: str, **fields: Any) -> None:
    exc_info = fields.pop("exc_info", None)
    logger.log(level, message, exc_info=exc_info, extra={"service": logger.name.removeprefix("kizuna."), "event": event, "fields": fields})


def service_instance_id(service: str) -> str:
    explicit = os.getenv("KIZUNA_SERVICE_INSTANCE_ID", "").strip()
    return explicit or f"{service}:{socket.gethostname()}:{os.getpid()}"


def record_service_heartbeat(db: Session, service_key: str, instance_id: str, *, status: str = "ready", details: dict[str, Any] | None = None) -> ServiceHeartbeat:
    now = utcnow()
    item = db.scalar(select(ServiceHeartbeat).where(ServiceHeartbeat.service_key == service_key, ServiceHeartbeat.instance_id == instance_id))
    if item is None:
        item = ServiceHeartbeat(service_key=service_key, instance_id=instance_id, status=status, details=details or {}, started_at=now, last_seen=now)
        db.add(item)
    else:
        item.status = status
        item.details = details or {}
        item.last_seen = now
    db.flush()
    return item


class ServiceHeartbeatLoop:
    def __init__(self, service_key: str, *, details: dict[str, Any] | None = None):
        self.service_key = service_key
        self.instance_id = service_instance_id(service_key)
        self.details = details or {}
        self.logger = service_logger(service_key)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"{service_key}-heartbeat", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        interval = max(5, settings.service_heartbeat_seconds)
        next_log = 0.0
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    record_service_heartbeat(db, self.service_key, self.instance_id, details=self.details)
                    db.commit()
            except Exception:
                if monotonic() >= next_log:
                    log_event(self.logger, logging.WARNING, "heartbeat_write_failed", "Could not write the service heartbeat", exc_info=True)
                    next_log = monotonic() + 60
            self._stop.wait(interval)
