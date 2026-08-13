from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


SMTP_HOST = os.getenv("KIZUNA_SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("KIZUNA_SMTP_PORT", "587"))
SMTP_USER = os.getenv("KIZUNA_SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("KIZUNA_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("KIZUNA_SMTP_FROM_EMAIL", "").strip()
SMTP_FROM_NAME = os.getenv("KIZUNA_SMTP_FROM_NAME", "Kizuna Studio").strip()
SMTP_STARTTLS = os.getenv("KIZUNA_SMTP_STARTTLS", "true").lower() in {"1", "true", "yes"}
SMTP_SSL = os.getenv("KIZUNA_SMTP_SSL", "false").lower() in {"1", "true", "yes"}


def ready() -> bool:
    return bool(SMTP_HOST and SMTP_FROM)


def send_text(to_address: str, subject: str, body: str) -> tuple[bool, str]:
    if not ready():
        return False, "SMTP is not configured"
    message = EmailMessage()
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    message["To"] = to_address.replace("\r", "").replace("\n", "")
    message["Subject"] = subject.replace("\r", " ").replace("\n", " ")[:180]
    message.set_content(body)
    try:
        client_class = smtplib.SMTP_SSL if SMTP_SSL else smtplib.SMTP
        with client_class(SMTP_HOST, SMTP_PORT, timeout=20) as client:
            if SMTP_STARTTLS and not SMTP_SSL:
                client.starttls()
            if SMTP_USER:
                client.login(SMTP_USER, SMTP_PASSWORD)
            client.send_message(message)
        return True, "sent"
    except (OSError, smtplib.SMTPException) as exc:
        return False, str(exc)[:500]
