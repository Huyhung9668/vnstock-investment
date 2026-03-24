from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


DictStrAny = dict[str, Any]


def send_email_summary(summary: dict[str, Any], config: dict[str, Any] | None = None) -> list[str]:
    warnings: list[str] = []

    if not isinstance(summary, dict):
        return ["Email notifier skipped: malformed summary."]

    normalized_config = config if isinstance(config, dict) else {}
    notifier_config = normalized_config.get("email", {})
    if not isinstance(notifier_config, dict):
        return ["Email notifier skipped: invalid config."]

    enabled = bool(notifier_config.get("enabled", False))
    if not enabled:
        return []

    recipient = str(notifier_config.get("to") or os.getenv("REPORT_EMAIL_TO") or "").strip()
    sender = str(notifier_config.get("from") or os.getenv("REPORT_EMAIL_FROM") or "").strip()
    smtp_host = str(notifier_config.get("host") or os.getenv("REPORT_EMAIL_HOST") or "").strip()
    smtp_port_raw = notifier_config.get("port") or os.getenv("REPORT_EMAIL_PORT") or 587
    smtp_username = str(notifier_config.get("username") or os.getenv("REPORT_EMAIL_USERNAME") or "").strip()
    smtp_password = str(notifier_config.get("password") or os.getenv("REPORT_EMAIL_PASSWORD") or "").strip()
    subject = str(notifier_config.get("subject") or "Daily run summary").strip()

    if not recipient or not sender or not smtp_host:
        return ["Email notifier skipped: missing credentials."]

    message = _build_summary_message(summary)

    try:
        smtp_port = int(smtp_port_raw)
        _send_email_message(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=message,
        )
    except Exception as exc:
        warnings.append(f"Email notifier skipped: {type(exc).__name__}: {exc}")
        return warnings

    return warnings


def _build_summary_message(summary: DictStrAny) -> str:
    return "\n".join(
        [
            "Daily run summary",
            f"total_symbols: {summary.get('total_symbols', 0)}",
            f"success_count: {summary.get('success_count', 0)}",
            f"failed_count: {summary.get('failed_count', 0)}",
            f"warning_count: {summary.get('warning_count', 0)}",
            f"files_created: {summary.get('files_created', [])}",
        ]
    )


def _send_email_message(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if smtp_username:
            smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)
