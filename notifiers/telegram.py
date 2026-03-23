from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled

    def _build_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str) -> bool:
        if not self.enabled:
            logger.info("Telegram notifier disabled.")
            return False

        try:
            response = requests.post(
                self._build_url(),
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            if response.status_code != 200:
                logger.warning("Telegram send failed: %s", response.text)
                return False
            return True
        except Exception as exc:
            logger.warning("Telegram error: %s", exc)
            return False


def build_daily_summary_message(summary: dict[str, Any]) -> str:
    failed = int(summary.get("failed", 0) or 0)
    execution_quality = str(summary.get("execution_quality", "")).strip().lower()
    if failed > 0:
        status = "PARTIAL"
    elif execution_quality == "degraded":
        status = "DEGRADED"
    else:
        status = "SUCCESS"

    lines: list[str] = [
        "*Daily Run Report*",
        f"Status: {status}",
        f"Run ID: `{summary.get('run_id')}`",
        "",
        "*Stats*",
        f"- Total scanned: {summary.get('total')}",
        f"- Selected: {len(summary.get('symbols_selected', []))}",
        f"- Success: {summary.get('success')}",
        f"- Failed: {failed}",
        f"- Quality: {summary.get('execution_quality', 'unknown')}",
        "",
        "*Headline*",
        str(summary.get("headline", "Chua co headline")),
        "",
        "*Top 10*",
        ", ".join(summary.get("symbols_selected", [])[:10]) or "N/A",
        "",
        "*Warnings*",
    ]

    warnings = summary.get("warnings", [])
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings[:5]])
    else:
        lines.append("None")

    next_actions = summary.get("next_actions", [])
    if isinstance(next_actions, list) and next_actions:
        lines.append("")
        lines.append("*Next Actions*")
        lines.extend([f"- {item}" for item in next_actions[:3]])

    lines.append("")
    lines.append("*Artifacts*")
    lines.append(f"{summary.get('manifest_path', 'N/A')}")

    return "\n".join(lines)
