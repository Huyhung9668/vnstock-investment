from __future__ import annotations

from typing import Any

import pandas as pd


def _risk_penalty(risk_tags: list[str]) -> float:
    if not risk_tags:
        return 0.0
    return min(len(risk_tags) * 0.15, 0.6)


def _catalyst_bonus(catalyst_tags: list[str]) -> float:
    if not catalyst_tags:
        return 0.0
    return min(len(catalyst_tags) * 0.12, 0.5)


def score_symbol_news_summary(summary: dict[str, Any]) -> dict[str, Any]:
    news_count = int(summary.get("news_count", 0))
    news_signal = float(summary.get("news_signal", 0.0))
    catalyst_tags = list(summary.get("catalyst_tags", []))
    risk_tags = list(summary.get("risk_tags", []))
    themes = list(summary.get("themes", []))
    sentiment_summary = str(summary.get("sentiment_summary", "Mixed to neutral news flow."))

    catalyst_bonus = _catalyst_bonus(catalyst_tags)
    risk_penalty = _risk_penalty(risk_tags)

    normalized_news_score = max(news_signal, -3.0)
    normalized_news_score = min(normalized_news_score, 3.0)
    normalized_news_score = (normalized_news_score + 3.0) / 6.0

    final_news_score = (normalized_news_score + catalyst_bonus - risk_penalty)
    final_news_score = max(min(final_news_score, 1.0), 0.0)

    return {
        "symbol": summary.get("symbol", ""),
        "news_count": news_count,
        "news_signal": news_signal,
        "catalyst_tags": catalyst_tags,
        "risk_tags": risk_tags,
        "themes": themes,
        "sentiment_summary": sentiment_summary,
        "headline_digest": list(summary.get("headline_digest", [])),
        "catalyst_bonus": catalyst_bonus,
        "risk_penalty": risk_penalty,
        "news_score": final_news_score,
    }


def merge_news_scores_into_universe(
    universe_df: pd.DataFrame,
    symbol_summaries: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    working_df = universe_df.copy()

    scored_rows = [
        score_symbol_news_summary(summary)
        for summary in symbol_summaries.values()
    ]

    if not scored_rows:
        if "news_signal" not in working_df.columns:
            working_df["news_signal"] = 0.0
        if "news_score" not in working_df.columns:
            working_df["news_score"] = 0.0
        if "sentiment_summary" not in working_df.columns:
            working_df["sentiment_summary"] = "No material news detected."
        if "catalyst_tags" not in working_df.columns:
            working_df["catalyst_tags"] = ""
        if "risk_tags" not in working_df.columns:
            working_df["risk_tags"] = ""
        if "themes" not in working_df.columns:
            working_df["themes"] = ""
        return working_df

    existing_news_columns = [
        "news_count",
        "news_signal",
        "news_score",
        "sentiment_summary",
        "catalyst_tags",
        "risk_tags",
        "themes",
    ]
    columns_to_drop = [column for column in existing_news_columns if column in working_df.columns]
    if columns_to_drop:
        working_df = working_df.drop(columns=columns_to_drop)

    news_df = pd.DataFrame(scored_rows)
    news_df["symbol"] = news_df["symbol"].astype(str).str.upper()
    working_df["symbol"] = working_df["symbol"].astype(str).str.upper()

    merged_df = working_df.merge(
        news_df[
            [
                "symbol",
                "news_count",
                "news_signal",
                "news_score",
                "sentiment_summary",
                "catalyst_tags",
                "risk_tags",
                "themes",
            ]
        ],
        on="symbol",
        how="left",
    )

    merged_df["news_count"] = pd.to_numeric(merged_df["news_count"], errors="coerce").fillna(0).astype(int)
    merged_df["news_signal"] = pd.to_numeric(merged_df["news_signal"], errors="coerce").fillna(0.0)
    merged_df["news_score"] = pd.to_numeric(merged_df["news_score"], errors="coerce").fillna(0.0)
    merged_df["sentiment_summary"] = merged_df["sentiment_summary"].fillna("No material news detected.")
    merged_df["catalyst_tags"] = merged_df["catalyst_tags"].apply(
        lambda value: ",".join(value) if isinstance(value, list) else (value or "")
    )
    merged_df["risk_tags"] = merged_df["risk_tags"].apply(
        lambda value: ",".join(value) if isinstance(value, list) else (value or "")
    )
    merged_df["themes"] = merged_df["themes"].apply(
        lambda value: ",".join(value) if isinstance(value, list) else (value or "")
    )

    return merged_df
