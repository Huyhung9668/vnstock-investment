from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_macro_context(
    *,
    market_overview: dict[str, Any] | None,
    market_news_summary: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_news = dict(market_news_summary or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    regime = _ensure_dict(normalized_market.get("regime"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    explanation = _text(regime.get("explanation"))
    positive_ratio = breadth.get("positive_ratio")
    themes = _normalize_string_list(normalized_market.get("market_themes"))
    headline_digest = _normalize_string_list(normalized_news.get("headline_digest"))

    summary_parts: list[str] = []
    if explanation:
        summary_parts.append(explanation)
    if positive_ratio is not None:
        summary_parts.append(f"Do rong thi truong positive_ratio = {_fmt(positive_ratio)}.")
    if themes:
        summary_parts.append(f"Theme dang noi bat: {', '.join(themes[:3])}.")
    if not summary_parts:
        summary_parts.append("Chua du du lieu vi mo de dua ra boi canh manh.")

    sentiment = "neutral"
    if isinstance(positive_ratio, (int, float)):
        if positive_ratio >= 0.6:
            sentiment = "supportive"
        elif positive_ratio <= 0.4:
            sentiment = "fragile"

    if any("degraded" in warning.lower() for warning in normalized_warnings):
        sentiment = "cautious"

    return {
        "status": "ready",
        "sentiment": sentiment,
        "summary": " ".join(summary_parts),
        "macro_points": headline_digest[:5],
        "themes": themes[:5],
        "warning_count": len(normalized_warnings),
    }


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)
