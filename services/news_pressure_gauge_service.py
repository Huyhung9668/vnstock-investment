from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]

THEME_KEYWORDS = {
    "global_risk": ["fed", "dxy", "brent", "oil", "geopolit", "war", "yield", "dow", "nasdaq", "s&p"],
    "domestic_policy": ["sbv", "policy", "nghị định", "thông tư", "tỷ giá", "lãi suất"],
    "earnings": ["quarter", "earnings", "profit", "guidance", "kqkd", "lợi nhuận"],
    "legal_regulatory": ["phạt", "investigation", "regulatory", "kiểm tra", "vi phạm"],
    "rumor_shock": ["rumor", "shock", "502", "bad gateway", "tin đồn", "sốc"],
}


def build_news_pressure_gauge(
    *,
    market_news_summary: dict[str, Any] | None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_news = dict(market_news_summary or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    headline_digest = _string_list(normalized_news.get("headline_digest"))
    items = headline_digest + normalized_warnings

    theme_hits: dict[str, list[str]] = {key: [] for key in THEME_KEYWORDS}
    for item in items:
        lower = item.lower()
        for theme, keywords in THEME_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                theme_hits[theme].append(item)

    hit_count = sum(len(values) for values in theme_hits.values())
    severity = "high" if hit_count >= 5 else "medium" if hit_count >= 2 else "low"
    horizon = "intraday" if theme_hits["rumor_shock"] else "swing" if hit_count else "medium-term"
    summary = (
        "Áp lực truyền thông hiện ở mức cao, nên ưu tiên xác nhận bằng giá và dòng tiền trước khi hành động."
        if severity == "high"
        else "Áp lực truyền thông đang ở mức vừa phải; headline có thể tạo biến động nhưng chưa đủ để thay thế tín hiệu thị trường."
        if severity == "medium"
        else "Hiện chưa có cụm tin đủ dày để tạo áp lực truyền thông mạnh lên thị trường."
    )

    return {
        "status": "ready",
        "severity": severity,
        "impact_horizon": horizon,
        "themes": {key: value[:3] for key, value in theme_hits.items() if value},
        "summary": summary,
        "analyst_brief": build_analyst_brief(
            insight=summary,
            evidence=[item for item in items[:3]],
            implication="Headline nên được dùng như lớp cảnh báo rủi ro và catalyst, không nên thay thế cấu trúc giá và độ rộng.",
            action="Tăng mức cảnh giác với các mã nhạy tin nếu chủ đề tin tức đang nghiêng sang shock hoặc pháp lý.",
            risk="Tin đồn và headline chưa xác nhận có thể gây rung lắc ngắn hạn nhưng không tạo xu hướng bền nếu dòng tiền không theo sau.",
        ),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
