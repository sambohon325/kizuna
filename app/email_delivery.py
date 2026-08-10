from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings


def smtp_ready() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_email(to_email: str, subject: str, text_body: str, html_body: str = "") -> None:
    if not smtp_ready():
        raise RuntimeError("SMTP delivery is not configured")
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    client_class = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    with client_class(settings.smtp_host, settings.smtp_port, timeout=20) as client:
        if settings.smtp_starttls and not settings.smtp_ssl:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
