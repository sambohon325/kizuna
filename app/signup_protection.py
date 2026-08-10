from __future__ import annotations

import json
from urllib import parse, request

from app.config import settings


def turnstile_ready() -> bool:
    return bool(settings.turnstile_site_key and settings.turnstile_secret_key)


def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    if not turnstile_ready() or not token:
        return False
    payload = {"secret": settings.turnstile_secret_key, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    encoded = parse.urlencode(payload).encode()
    call = request.Request("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=encoded, method="POST")
    try:
        with request.urlopen(call, timeout=10) as response:
            result = json.loads(response.read().decode())
        expected_host = parse.urlparse(settings.public_url).hostname
        return result.get("success") is True and (not expected_host or result.get("hostname") == expected_host)
    except Exception:
        return False
