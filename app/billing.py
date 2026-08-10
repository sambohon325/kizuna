from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib import error, parse, request

from app.config import settings


ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def stripe_ready() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_webhook_secret and settings.stripe_creator_price_id)


def stripe_request(path: str, fields: dict[str, str]) -> dict:
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe is not configured")
    encoded = parse.urlencode(fields).encode()
    auth = base64.b64encode(f"{settings.stripe_secret_key}:".encode()).decode()
    call = request.Request(f"https://api.stripe.com/v1/{path.lstrip('/')}", data=encoded, method="POST", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with request.urlopen(call, timeout=20) as response:
            return json.loads(response.read().decode())
    except error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode()).get("error", {}).get("message", "Stripe rejected the request")
        except Exception:
            message = "Stripe rejected the request"
        raise RuntimeError(message) from exc


def verify_stripe_event(payload: bytes, signature: str, tolerance_seconds: int = 300) -> dict:
    if not settings.stripe_webhook_secret:
        raise ValueError("Stripe webhook signing is not configured")
    pieces: dict[str, list[str]] = {}
    for part in signature.split(","):
        key, _, value = part.partition("=")
        pieces.setdefault(key, []).append(value)
    try:
        timestamp = int(pieces["t"][0])
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError("Invalid Stripe signature") from exc
    if abs(int(time.time()) - timestamp) > tolerance_seconds:
        raise ValueError("Expired Stripe signature")
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(settings.stripe_webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in pieces.get("v1", [])):
        raise ValueError("Invalid Stripe signature")
    return json.loads(payload.decode())


def stripe_timestamp(value: int | float | None) -> datetime | None:
    return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None) if value else None
