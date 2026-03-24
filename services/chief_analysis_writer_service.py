from __future__ import annotations

from datetime import datetime
from typing import Any


DictStrAny = dict[str, Any]


def build_chief_analysis(
    *,
    synthesis: dict[str, Any],
    generated_at: str | None = None,
    ai_analysis: dict[str, Any] | None = None,
) -> DictStrAny:
    normalized_synthesis = dict(synthesis or {})
    normalized_ai = dict(ai_analysis or {})
    effective_generated_at = generated_at or datetime.now().isoformat()

    title = normalized_ai.get("headline") or "Nhan Dinh Thi Truong & Ke Hoach Hanh Dong"
    summary = normalized_ai.get("market_story") or normalized_synthesis.get("conclusion") or "Chua co tong ket narrative."
    portfolio_focus = normalized_ai.get("portfolio_focus") or _portfolio_focus(normalized_synthesis)

    sections = [
        {
            "title": "Tom Tat Dieu Hanh",
            "paragraphs": [
                summary,
                f"Trang thai hanh dong uu tien hien tai: {_string_or_none(normalized_synthesis.get('stance')) or 'neutral'}.",
                _string_or_none(normalized_synthesis.get("data_quality_note")) or "Can tiep tuc doi chieu du lieu truoc khi hanh dong.",
            ],
        },
        {
            "title": "Tin Hieu Vi Mo Va Sentiment",
            "bullets": _normalize_string_list(normalized_synthesis.get("macro_and_sentiment")),
        },
        {
            "title": "Trang Thai Thi Truong",
            "bullets": _normalize_string_list(normalized_synthesis.get("market_state")),
        },
        {
            "title": "Dong Tien Va Luan Chuyen Nganh",
            "bullets": _normalize_string_list(normalized_synthesis.get("flow_of_funds"))
            + _normalize_string_list(normalized_synthesis.get("sector_strength")),
        },
        {
            "title": "Co Hoi Dang Chu Y",
            "bullets": _stock_focus_bullets(normalized_synthesis.get("top_stock_focus")),
        },
        {
            "title": "Ke Hoach Hanh Dong",
            "paragraphs": [portfolio_focus] if portfolio_focus else [],
            "bullets": _normalize_string_list(normalized_synthesis.get("action_plan"))
            + _normalize_string_list(normalized_ai.get("action_plan")),
        },
        {
            "title": "Rui Ro Va Dieu Kien Vo Hieu",
            "bullets": _normalize_string_list(normalized_synthesis.get("risk_watch"))
            + _normalize_string_list(normalized_ai.get("risk_alerts")),
        },
        {
            "title": "Ket Luan",
            "paragraphs": [
                _string_or_none(normalized_synthesis.get("conclusion")) or "Chua co ket luan cuoi.",
            ],
        },
    ]

    return {
        "title": title,
        "update_line": f"Cap nhat: {effective_generated_at}",
        "summary": summary,
        "stance": normalized_synthesis.get("stance"),
        "confidence": normalized_synthesis.get("confidence"),
        "sections": sections,
    }


def _stock_focus_bullets(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return ["Chua co danh sach co hoi noi bat."]

    bullets: list[str] = []
    for item in payload[:5]:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        thesis = str(item.get("thesis", "")).strip()
        trigger = str(item.get("trigger", "")).strip()
        risk_reward = str(item.get("risk_reward", "")).strip()
        if not symbol:
            continue
        message = f"{symbol}: {thesis or 'Can review them luan diem'}"
        if trigger:
            message += f" Trigger = {trigger}."
        if risk_reward:
            message += f" Risk/reward = {risk_reward}."
        bullets.append(message)

    return bullets or ["Chua co danh sach co hoi noi bat."]


def _portfolio_focus(synthesis: DictStrAny) -> str:
    stance = _string_or_none(synthesis.get("stance")) or "neutral"
    confidence = _string_or_none(synthesis.get("confidence")) or "low"
    return f"Portfolio focus hien tai nghieng ve {stance}, voi muc do tin cay du lieu o muc {confidence}."


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
