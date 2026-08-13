from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


STEWARD_URL = os.getenv("KIZUNA_ACCOUNT_STEWARD_URL", "").strip()
STEWARD_SECRET = os.getenv("KIZUNA_ACCOUNT_STEWARD_SECRET", "")
BETA_AUTO_INVITE = os.getenv("KIZUNA_BETA_AUTO_INVITE", "false").lower() in {"1", "true", "yes"}
BETA_COHORT = os.getenv("KIZUNA_BETA_COHORT", "private-beta").strip() or "private-beta"


class AccountStewardError(RuntimeError):
    pass


def readiness() -> dict[str, Any]:
    return {"ready": bool(STEWARD_URL.startswith(("https://", "http://")) and len(STEWARD_SECRET) >= 32), "auto_invite": BETA_AUTO_INVITE, "cohort": BETA_COHORT}


def request_id(application_id: int, email: str) -> str:
    suffix = hashlib.sha256(email.strip().casefold().encode()).hexdigest()[:16]
    return f"beta-{application_id}-{suffix}"


def provision_beta(application: dict[str, Any]) -> dict[str, Any]:
    if not readiness()["ready"]:
        raise AccountStewardError("Account Steward connection is not configured")
    payload = {
        "request_id": request_id(int(application["id"]), str(application["email"])),
        "application_id": str(application["id"]),
        "email": str(application["email"]),
        "display_name": str(application["name"]),
        "experience": str(application["experience"]),
        "creator_type": str(application["creator_type"]),
        "cohort": BETA_COHORT,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(STEWARD_SECRET.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    request = Request(STEWARD_URL, data=body, headers={"Content-Type": "application/json", "X-Kizuna-Timestamp": timestamp, "X-Kizuna-Signature": f"sha256={signature}"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise AccountStewardError(f"Account service returned {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AccountStewardError(f"Could not reach the account service: {exc}") from exc
