from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ScoreWeights:
    liquidity: float = 0.18
    trend: float = 0.20
    relative_strength: float = 0.20
    volume_expansion: float = 0.15
    sector_strength: float = 0.12
    catalyst_signal: float = 0.15


def _safe_rank_pct(series: pd.Series, ascending: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(0.0, index=series.index)
    return numeric.rank(pct=True, ascending=ascending, method="average").fillna(0.0)


def _normalize_binary_flag(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0, upper=1)


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()

    defaults: dict[str, Any] = {
        "symbol": "",
        "exchange": "UNKNOWN",
        "avg_volume": 0.0,
        "last_price": 0.0,
        "return_3m": 0.0,
        "return_1y": 0.0,
        "volume_ratio_20d": 1.0,
        "sector": "UNKNOWN",
        "sector_return_1m": 0.0,
        "news_signal": 0.0,
        "news_score": 0.0,
        "risk_halt_flag": 0,
        "risk_low_liquidity_flag": 0,
        "risk_extreme_volatility_flag": 0,
    }

    for column, default_value in defaults.items():
        if column not in working_df.columns:
            working_df[column] = default_value

    return working_df


def build_component_scores(
    df: pd.DataFrame,
    weights: ScoreWeights | None = None,
) -> pd.DataFrame:
    scoring_weights = weights or ScoreWeights()
    working_df = ensure_required_columns(df)

    working_df["liquidity_score"] = _safe_rank_pct(working_df["avg_volume"], ascending=True)

    trend_input = (
        pd.to_numeric(working_df["return_3m"], errors="coerce").fillna(0.0) * 0.6
        + pd.to_numeric(working_df["return_1y"], errors="coerce").fillna(0.0) * 0.4
    )
    working_df["trend_score"] = _safe_rank_pct(trend_input, ascending=True)

    working_df["relative_strength_score"] = _safe_rank_pct(
        working_df["return_3m"],
        ascending=True,
    )

    working_df["volume_expansion_score"] = _safe_rank_pct(
        working_df["volume_ratio_20d"],
        ascending=True,
    )

    working_df["sector_strength_score"] = _safe_rank_pct(
        working_df["sector_return_1m"],
        ascending=True,
    )

    catalyst_base = pd.to_numeric(working_df["news_score"], errors="coerce").fillna(0.0)
    catalyst_overlay = pd.to_numeric(working_df["news_signal"], errors="coerce").fillna(0.0)
    catalyst_input = catalyst_base * 0.7 + _safe_rank_pct(catalyst_overlay, ascending=True) * 0.3
    working_df["catalyst_signal_score"] = catalyst_input.clip(lower=0.0, upper=1.0)

    working_df["raw_score"] = (
        working_df["liquidity_score"] * scoring_weights.liquidity
        + working_df["trend_score"] * scoring_weights.trend
        + working_df["relative_strength_score"] * scoring_weights.relative_strength
        + working_df["volume_expansion_score"] * scoring_weights.volume_expansion
        + working_df["sector_strength_score"] * scoring_weights.sector_strength
        + working_df["catalyst_signal_score"] * scoring_weights.catalyst_signal
    )

    return working_df


def apply_risk_flags(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()

    working_df["risk_halt_flag"] = _normalize_binary_flag(working_df["risk_halt_flag"])
    working_df["risk_low_liquidity_flag"] = _normalize_binary_flag(
        working_df["risk_low_liquidity_flag"]
    )
    working_df["risk_extreme_volatility_flag"] = _normalize_binary_flag(
        working_df["risk_extreme_volatility_flag"]
    )

    working_df["risk_penalty"] = (
        working_df["risk_halt_flag"] * 0.50
        + working_df["risk_low_liquidity_flag"] * 0.20
        + working_df["risk_extreme_volatility_flag"] * 0.15
    )

    working_df["final_score"] = (working_df["raw_score"] - working_df["risk_penalty"]).clip(lower=0.0)
    return working_df


def add_rank_columns(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    working_df = working_df.sort_values(
        by=["final_score", "raw_score", "avg_volume", "return_3m"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    working_df["rank"] = range(1, len(working_df) + 1)
    return working_df


def score_universe(
    df: pd.DataFrame,
    weights: ScoreWeights | None = None,
) -> pd.DataFrame:
    scored_df = build_component_scores(df, weights=weights)
    scored_df = apply_risk_flags(scored_df)
    scored_df = add_rank_columns(scored_df)
    return scored_df
