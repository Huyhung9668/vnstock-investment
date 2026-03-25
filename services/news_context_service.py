from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_news_context(
    *,
    market_news_summary: dict[str, Any] | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
) -> DictStrAny:
    market_summary = dict(market_news_summary or {})
    payloads = symbol_payloads or {}

    symbol_rows: list[DictStrAny] = []
    for symbol, payload in sorted(payloads.items()):
        if not isinstance(payload, dict):
            continue
        news_summary = dict(payload.get("news_summary") or {})
        if not news_summary:
            continue
        symbol_rows.append(
            {
                "symbol": str(symbol).strip().upper(),
                "news_count": news_summary.get("news_count", 0),
                "sentiment_summary": news_summary.get("sentiment_summary") or news_summary.get("summary"),
                "catalyst_tags": list(news_summary.get("catalyst_tags") or []),
                "risk_tags": list(news_summary.get("risk_tags") or []),
            }
        )

    active_symbols = [row["symbol"] for row in symbol_rows if row.get("news_count")]
    market_sentiment = str(market_summary.get("market_sentiment_summary", "")).strip()
    brief = build_analyst_brief(
        insight=(
            f"Dòng tin hiện hỗ trợ việc theo dõi {', '.join(active_symbols[:3])}."
            if active_symbols else "Hiện chưa có lớp tin tức đủ dày để tạo lợi thế thông tin rõ rệt cho nhóm mã theo dõi."
        ),
        evidence=([market_sentiment] if market_sentiment else []) + [
            f"Có {len(active_symbols)} mã trong nhóm ưu tiên xuất hiện ngữ cảnh tin tức." if active_symbols else "Tin tức từng mã hiện còn mỏng."
        ],
        implication="Tin tức nên được dùng như lớp xác nhận catalyst hoặc cảnh báo rủi ro, không nên dùng thay cho cấu trúc giá.",
        action="Ưu tiên đối chiếu tin tức với phản ứng giá ở các mã đầu danh sách trước khi nâng mức theo dõi.",
        risk="Nếu tin tức không đi cùng thanh khoản và giá, xác suất nhiễu sẽ rất cao.",
    )

    return {
        "status": "ready" if market_summary or symbol_rows else "missing",
        "summary": market_sentiment or "Chưa có đủ ngữ cảnh tin tức đáng kể.",
        "market_sentiment_summary": market_sentiment,
        "symbol_rows": symbol_rows[:10],
        "analyst_brief": brief,
    }
