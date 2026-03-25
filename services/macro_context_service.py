from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


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
        summary_parts.append(f"Độ rộng thị trường hiện vào khoảng {_fmt(positive_ratio)}.")
    if themes:
        summary_parts.append(f"Các theme nổi bật gồm: {', '.join(themes[:3])}.")
    if not summary_parts:
        summary_parts.append("Chưa đủ dữ liệu vĩ mô để đưa ra bối cảnh mạnh.")

    sentiment = "neutral"
    if isinstance(positive_ratio, (int, float)):
        if positive_ratio >= 0.6:
            sentiment = "supportive"
        elif positive_ratio <= 0.4:
            sentiment = "fragile"
    if any("degraded" in warning.lower() for warning in normalized_warnings):
        sentiment = "cautious"

    brief = build_analyst_brief(
        insight=(
            "Bối cảnh vĩ mô và tâm lý đang ủng hộ trạng thái tích cực có chọn lọc."
            if sentiment == "supportive"
            else "Bối cảnh vĩ mô và tâm lý hiện nghiêng về phòng thủ, chưa phù hợp để mua lan tỏa."
            if sentiment in {"fragile", "cautious"}
            else "Bối cảnh vĩ mô đang ở trạng thái trung tính, cần thêm xác nhận từ dòng tiền và độ rộng."
        ),
        evidence=summary_parts[:3] + headline_digest[:2],
        implication=(
            "Ưu tiên đánh giá chất lượng dòng tiền thay vì chỉ nhìn biến động giá ngắn hạn."
        ),
        action=(
            "Giữ danh sách theo dõi hẹp và chỉ nâng mức cam kết vốn khi thị trường xác nhận tốt hơn."
        ),
        risk=(
            "Nếu độ rộng tiếp tục yếu, các nhịp hồi ngắn dễ trở thành cơ hội thoát hàng hơn là mở vị thế mới."
        ),
    )

    return {
        "status": "ready",
        "sentiment": sentiment,
        "summary": " ".join(summary_parts),
        "macro_points": headline_digest[:5],
        "themes": themes[:5],
        "warning_count": len(normalized_warnings),
        "analyst_brief": brief,
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
