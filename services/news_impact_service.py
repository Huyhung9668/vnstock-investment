from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_news_impact(
    *,
    market_news_summary: dict[str, Any] | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    market_news = dict(market_news_summary or {})
    payloads = symbol_payloads or {}
    warning_rows = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    headline_digest = [str(item).strip() for item in (market_news.get("headline_digest") or []) if str(item).strip()]
    market_sentiment = str(market_news.get("market_sentiment_summary", "")).strip()
    themes = [str(item).strip() for item in (market_news.get("market_themes") or []) if str(item).strip()]
    market_risks = [str(item).strip() for item in (market_news.get("market_risk_tags") or []) if str(item).strip()]

    catalysts: list[str] = []
    negative_news: list[str] = []
    shock_news: list[str] = []
    symbol_notes: list[str] = []

    for symbol, payload in sorted(payloads.items()):
        if not isinstance(payload, dict):
            continue
        news_summary = dict(payload.get("news_summary") or {})
        latest = dict(news_summary.get("latest") or {})
        title = str(latest.get("title") or latest.get("headline") or "").strip()
        if title:
            symbol_notes.append(f"{str(symbol).strip().upper()}: {title}")
        for tag in news_summary.get("catalyst_tags") or []:
            text = str(tag).strip()
            if text:
                catalysts.append(f"{str(symbol).strip().upper()}: {text}")
        for tag in news_summary.get("risk_tags") or []:
            text = str(tag).strip()
            if text:
                negative_news.append(f"{str(symbol).strip().upper()}: {text}")

    for item in headline_digest:
        lowered = item.lower()
        if any(keyword in lowered for keyword in ["sốc", "shock", "giảm sâu", "panic", "khẩn", "downgrade"]):
            shock_news.append(item)
        elif any(keyword in lowered for keyword in ["tăng", "mở rộng", "ký", "lợi nhuận", "nâng", "hỗ trợ"]):
            catalysts.append(item)
        else:
            negative_news.append(item)

    for warning in warning_rows:
        if "502" in warning or "failed" in warning.lower() or "error" in warning.lower():
            shock_news.append(warning)

    headline = _build_headline(market_sentiment=market_sentiment, catalysts=catalysts, negative_news=negative_news, shock_news=shock_news)
    return {
        "status": "ready" if (market_news or payloads or warning_rows) else "missing",
        "headline": headline,
        "market_sentiment": market_sentiment,
        "themes": themes[:5],
        "positive_items": _unique_keep_order(catalysts)[:5],
        "negative_items": _unique_keep_order(negative_news + market_risks)[:5],
        "shock_items": _unique_keep_order(shock_news)[:5],
        "symbol_notes": _unique_keep_order(symbol_notes)[:5],
        "conclusion": _build_conclusion(catalysts=catalysts, negative_news=negative_news, shock_news=shock_news),
    }


def _build_headline(*, market_sentiment: str, catalysts: list[str], negative_news: list[str], shock_news: list[str]) -> str:
    if shock_news:
        return "Thị trường đang chịu tác động từ các tín hiệu nhiễu hoặc tin bất lợi; cần ưu tiên phản ứng giá thay vì đoán trước diễn biến."
    if catalysts and not negative_news:
        return "Tin tức đang thiên về hỗ trợ, nhưng vẫn cần dòng tiền xác nhận thì hiệu ứng mới bền."
    if market_sentiment and market_sentiment.lower() != "no market-wide news detected.":
        return market_sentiment
    return "Hiện chưa có cụm tin tức đủ mạnh để đảo chiều tâm lý toàn thị trường; biến động giá vẫn là tín hiệu quan trọng hơn."


def _build_conclusion(*, catalysts: list[str], negative_news: list[str], shock_news: list[str]) -> str:
    if shock_news:
        return "Tin xấu chỉ thực sự nguy hiểm khi đi kèm bán mạnh và làm gãy cấu trúc giá; ngược lại, nếu thị trường hấp thụ được thì đây có thể là phép thử sức mạnh dòng tiền."
    if catalysts:
        return "Tin tốt nên được xem là chất xúc tác hỗ trợ; chỉ nên hành động mạnh hơn khi giá phản ứng tích cực và thanh khoản đồng thuận."
    if negative_news:
        return "Thiếu catalyst mạnh khiến thị trường dễ quay lại trạng thái giao dịch phòng thủ và chọn lọc."
    return "Lúc này chưa nên đặt cược theo headline, mà nên ưu tiên xác nhận từ dòng tiền và cấu trúc giá."


def _unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output
