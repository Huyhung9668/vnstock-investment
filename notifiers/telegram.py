from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)
MAX_TELEGRAM_TEXT_LENGTH = 3500


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
            if len(str(text)) <= MAX_TELEGRAM_TEXT_LENGTH:
                response = self._post_message(text=text, parse_mode="Markdown")
                if response.status_code == 200:
                    return True
                logger.warning("Telegram send failed: %s", response.text)
                if response.status_code == 400:
                    return self._send_chunked_plain_text(_plain_text_message(text))
                return False

            logger.info("Telegram message exceeds safe length; using chunked plain text mode.")
            return self._send_chunked_plain_text(_plain_text_message(text))
        except Exception as exc:
            logger.warning("Telegram error: %s", exc)
            return False

    def _send_chunked_plain_text(self, text: str) -> bool:
        chunks = _chunk_message(text, max_length=MAX_TELEGRAM_TEXT_LENGTH)
        if not chunks:
            return False
        for index, chunk in enumerate(chunks, start=1):
            prefix = f"[{index}/{len(chunks)}]\n" if len(chunks) > 1 else ""
            response = self._post_message(text=prefix + chunk, parse_mode=None)
            if response.status_code != 200:
                logger.warning("Telegram plain text chunk %s failed: %s", index, response.text)
                return False
        logger.info("Telegram message sent successfully in %s chunk(s).", len(chunks))
        return True

    def _post_message(self, *, text: str, parse_mode: str | None) -> requests.Response:
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return requests.post(self._build_url(), json=payload, timeout=10)


def build_daily_summary_message(summary: dict[str, Any]) -> str:
    chief_analysis = summary.get("chief_analysis")
    if isinstance(chief_analysis, dict) and chief_analysis:
        rendered = _render_telegram_brief(chief_analysis, summary)
        if rendered.strip():
            return rendered
    return _render_fallback_narrative(summary)


def _render_telegram_brief(chief_analysis: dict[str, Any], summary: dict[str, Any]) -> str:
    lines: list[str] = []
    title = str(chief_analysis.get("title") or "Nhận Định Thị Trường").strip()
    update_line = str(chief_analysis.get("update_line") or f"Cập nhật: {summary.get('run_id', '')}").strip()
    summary_text = str(chief_analysis.get("summary") or summary.get("headline") or "").strip()
    sections = chief_analysis.get("sections") if isinstance(chief_analysis.get("sections"), list) else []

    lines.extend([title, update_line])
    if summary_text:
        lines.extend(["", summary_text])

    for index, section in enumerate(sections[:5], start=1):
        if not isinstance(section, dict):
            continue
        section_title = str(section.get("title") or "").strip()
        paragraphs = [str(item).strip() for item in section.get("paragraphs", []) if str(item).strip()] if isinstance(section.get("paragraphs"), list) else []
        bullets = [str(item).strip() for item in section.get("bullets", []) if str(item).strip()] if isinstance(section.get("bullets"), list) else []
        if not section_title:
            continue
        lines.extend(["", f"{index}. {section_title}"])
        if paragraphs:
            lines.append(paragraphs[0])
        if bullets and index >= 4:
            lines.extend([f"- {item}" for item in bullets[:3]])

    actions = _extract_section(sections, "Kế Hoạch Hành Động")
    risks = _extract_section(sections, "Rủi Ro Cần Theo Dõi")
    conclusion = _extract_section(sections, "Kết Luận")

    if actions:
        lines.extend(["", "6. Kế Hoạch Hành Động", actions[0]])
    if risks:
        lines.extend(["", "7. Rủi Ro Cần Theo Dõi", risks[0]])
    if conclusion:
        lines.extend(["", "8. Kết Luận", conclusion[0]])

    return "\n".join(lines).strip()


def _extract_section(sections: list[Any], title: str) -> list[str]:
    for section in sections:
        if not isinstance(section, dict):
            continue
        if str(section.get("title") or "").strip() != title:
            continue
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list):
            return []
        return [str(item).strip() for item in paragraphs if str(item).strip()]
    return []


def _render_fallback_narrative(summary: dict[str, Any]) -> str:
    headline = str(summary.get("ai_headline") or summary.get("headline") or "Nhận Định Thị Trường").strip()
    next_actions = summary.get("ai_action_plan") or summary.get("next_actions") or []
    symbols = summary.get("symbols_selected", [])[:5]
    watchlist = ", ".join(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip())
    action_text = "; ".join(str(item).strip() for item in next_actions[:2] if str(item).strip())
    body = "Thị trường hiện được tổng hợp từ pipeline nội bộ và ưu tiên lúc này là lọc ra các cổ phiếu còn đủ điều kiện theo dõi."
    if watchlist:
        body += f" Nhóm cần theo sát gồm {watchlist}."
    if action_text:
        body += f" Hướng hành động ưu tiên là: {action_text}."
    return "\n".join([headline, f"Cập nhật: {summary.get('run_id', '')}", "", body]).strip()


def _plain_text_message(text: str) -> str:
    sanitized = str(text)
    for marker in ("`", "*", "_"):
        sanitized = sanitized.replace(marker, "")
    return sanitized


def _chunk_message(text: str, *, max_length: int) -> list[str]:
    normalized = str(text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_length:
        return [normalized]
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_length:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= max_length:
            current = paragraph
            continue
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        for line in lines:
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= max_length:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = ""
            while len(line) > max_length:
                chunks.append(line[:max_length].rstrip())
                line = line[max_length:].lstrip()
            current = line
    if current:
        chunks.append(current)
    return chunks
