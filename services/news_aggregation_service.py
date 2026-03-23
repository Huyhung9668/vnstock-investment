from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


POSITIVE_KEYWORDS = {
    "tăng trưởng",
    "mở rộng",
    "ký kết",
    "thắng thầu",
    "lợi nhuận tăng",
    "doanh thu tăng",
    "cổ tức",
    "mua vào",
    "nâng hạng",
    "hưởng lợi",
    "breakout",
    "vượt đỉnh",
    "đột biến",
    "hợp tác",
    "đầu tư",
    "khởi công",
}

NEGATIVE_KEYWORDS = {
    "giảm",
    "thua lỗ",
    "bị phạt",
    "đình chỉ",
    "truy thu",
    "điều tra",
    "rủi ro",
    "áp lực bán",
    "pha loãng",
    "nợ xấu",
    "cảnh báo",
    "hủy",
    "suy giảm",
    "đứt gãy",
    "vi phạm",
    "bán giải chấp",
}

CATALYST_KEYWORDS = {
    "kết quả kinh doanh",
    "cổ tức",
    "thắng thầu",
    "hợp đồng",
    "mở rộng",
    "đầu tư công",
    "nâng hạng",
    "room tín dụng",
    "chia cổ tức",
    "mua cổ phiếu quỹ",
    "thoái vốn",
}

RISK_KEYWORDS = {
    "thua lỗ",
    "bị phạt",
    "điều tra",
    "truy thu",
    "cảnh báo",
    "hủy niêm yết",
    "giải chấp",
    "nợ xấu",
    "trích lập",
    "pha loãng",
}

THEME_RULES: dict[str, set[str]] = {
    "banking": {"ngân hàng", "tín dụng", "lãi suất", "nợ xấu", "room tín dụng"},
    "real_estate": {"bất động sản", "dự án", "pháp lý", "quỹ đất"},
    "steel": {"thép", "tôn", "giá quặng", "hòa phát"},
    "retail": {"bán lẻ", "tiêu dùng", "cửa hàng", "doanh thu chuỗi"},
    "technology": {"công nghệ", "chuyển đổi số", "phần mềm", "viễn thông"},
    "market_liquidity": {"thanh khoản", "khối lượng", "dòng tiền", "margin"},
    "macro_rates": {"lãi suất", "tỷ giá", "fed", "vĩ mô", "usd"},
}


@dataclass(frozen=True)
class NewsItem:
    symbol: str
    title: str
    summary: str
    source: str
    published_at: str
    url: str
    news_type: str  # symbol | market


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_symbol(symbol: str | None) -> str:
    return _normalize_text(symbol).upper() or "MARKET"


def _safe_timestamp(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return datetime.utcnow().isoformat()
    return text


def normalize_news_items(rows: list[dict[str, Any]]) -> list[NewsItem]:
    normalized: list[NewsItem] = []
    for row in rows:
        normalized.append(
            NewsItem(
                symbol=_normalize_symbol(row.get("symbol")),
                title=_normalize_text(row.get("title")),
                summary=_normalize_text(row.get("summary")),
                source=_normalize_text(row.get("source")) or "unknown",
                published_at=_safe_timestamp(row.get("published_at")),
                url=_normalize_text(row.get("url")),
                news_type=_normalize_text(row.get("news_type")) or "symbol",
            )
        )
    return normalized


def deduplicate_news(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[tuple[str, str]] = set()
    deduped: list[NewsItem] = []

    for item in items:
        dedupe_key = (
            item.symbol,
            f"{item.title.lower()}|{item.source.lower()}",
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(item)

    return deduped


def detect_themes(text: str) -> list[str]:
    lowered = text.lower()
    matched_themes: list[str] = []

    for theme, keywords in THEME_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            matched_themes.append(theme)

    return matched_themes


def extract_tags(text: str, keywords: set[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def analyze_news_item(item: NewsItem) -> dict[str, Any]:
    combined_text = f"{item.title}. {item.summary}".strip()
    sentiment_score = 0

    positive_hits = extract_tags(combined_text, POSITIVE_KEYWORDS)
    negative_hits = extract_tags(combined_text, NEGATIVE_KEYWORDS)
    catalyst_hits = extract_tags(combined_text, CATALYST_KEYWORDS)
    risk_hits = extract_tags(combined_text, RISK_KEYWORDS)
    themes = detect_themes(combined_text)

    sentiment_score += len(positive_hits)
    sentiment_score -= len(negative_hits)

    return {
        "symbol": item.symbol,
        "title": item.title,
        "summary": item.summary,
        "source": item.source,
        "published_at": item.published_at,
        "url": item.url,
        "news_type": item.news_type,
        "themes": themes,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "catalyst_tags": catalyst_hits,
        "risk_tags": risk_hits,
        "sentiment_score": sentiment_score,
    }


def aggregate_symbol_news(symbol: str, items: list[NewsItem]) -> dict[str, Any]:
    symbol_upper = _normalize_symbol(symbol)
    symbol_items = [item for item in items if item.symbol == symbol_upper]

    if not symbol_items:
        return {
            "symbol": symbol_upper,
            "news_count": 0,
            "news_signal": 0.0,
            "catalyst_tags": [],
            "risk_tags": [],
            "themes": [],
            "sentiment_summary": "No material news detected.",
            "headline_digest": [],
        }

    analyzed_rows = [analyze_news_item(item) for item in symbol_items]
    news_df = pd.DataFrame(analyzed_rows)

    catalyst_tags = sorted(
        {
            tag
            for tags in news_df["catalyst_tags"].tolist()
            for tag in tags
        }
    )
    risk_tags = sorted(
        {
            tag
            for tags in news_df["risk_tags"].tolist()
            for tag in tags
        }
    )
    themes = sorted(
        {
            theme
            for tags in news_df["themes"].tolist()
            for theme in tags
        }
    )

    sentiment_total = float(news_df["sentiment_score"].sum())
    news_count = int(len(news_df))
    news_signal = sentiment_total / max(news_count, 1)

    if news_signal >= 1:
        sentiment_summary = "Positive news flow."
    elif news_signal <= -1:
        sentiment_summary = "Negative news flow."
    else:
        sentiment_summary = "Mixed to neutral news flow."

    headline_digest = news_df.sort_values(
        by=["sentiment_score", "published_at"],
        ascending=[False, False],
    )["title"].head(5).tolist()

    return {
        "symbol": symbol_upper,
        "news_count": news_count,
        "news_signal": news_signal,
        "catalyst_tags": catalyst_tags,
        "risk_tags": risk_tags,
        "themes": themes,
        "sentiment_summary": sentiment_summary,
        "headline_digest": headline_digest,
    }


def aggregate_market_news(items: list[NewsItem]) -> dict[str, Any]:
    market_items = [item for item in items if item.news_type == "market" or item.symbol == "MARKET"]

    if not market_items:
        return {
            "market_themes": [],
            "market_risk_tags": [],
            "market_sentiment_summary": "No market-wide news detected.",
            "headline_digest": [],
        }

    analyzed_rows = [analyze_news_item(item) for item in market_items]
    news_df = pd.DataFrame(analyzed_rows)

    market_themes = sorted(
        {
            theme
            for tags in news_df["themes"].tolist()
            for theme in tags
        }
    )
    market_risk_tags = sorted(
        {
            tag
            for tags in news_df["risk_tags"].tolist()
            for tag in tags
        }
    )

    sentiment_total = float(news_df["sentiment_score"].sum())

    if sentiment_total > 2:
        summary = "Market news flow is broadly supportive."
    elif sentiment_total < -2:
        summary = "Market news flow is broadly risk-off."
    else:
        summary = "Market news flow is balanced to neutral."

    headlines = news_df.sort_values(
        by=["sentiment_score", "published_at"],
        ascending=[False, False],
    )["title"].head(10).tolist()

    return {
        "market_themes": market_themes,
        "market_risk_tags": market_risk_tags,
        "market_sentiment_summary": summary,
        "headline_digest": headlines,
    }


def aggregate_news(
    symbol_news_rows: list[dict[str, Any]],
    market_news_rows: list[dict[str, Any]],
    symbols: list[str],
) -> dict[str, Any]:
    all_rows = normalize_news_items(symbol_news_rows + market_news_rows)
    deduped_items = deduplicate_news(all_rows)

    symbol_summaries = {
        symbol.upper(): aggregate_symbol_news(symbol, deduped_items)
        for symbol in symbols
    }
    market_summary = aggregate_market_news(deduped_items)

    return {
        "symbol_summaries": symbol_summaries,
        "market_summary": market_summary,
        "news_items_total": len(deduped_items),
    }
