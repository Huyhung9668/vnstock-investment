from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from services.scoring_service import ScoreWeights, score_universe


def _safe_read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    return pd.read_csv(csv_path)


def _enrich_defaults(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()

    if "sector" not in working_df.columns:
        working_df["sector"] = "UNKNOWN"

    if "volume_ratio_20d" not in working_df.columns:
        working_df["volume_ratio_20d"] = 1.0

    if "news_signal" not in working_df.columns:
        working_df["news_signal"] = 0.0

    if "sector_return_1m" not in working_df.columns:
        sector_strength = (
            working_df.groupby("sector")["return_3m"].mean().rename("sector_return_1m")
        )
        working_df = working_df.merge(
            sector_strength,
            on="sector",
            how="left",
        )

    if "risk_halt_flag" not in working_df.columns:
        working_df["risk_halt_flag"] = 0

    if "risk_low_liquidity_flag" not in working_df.columns:
        working_df["risk_low_liquidity_flag"] = (
            pd.to_numeric(working_df.get("avg_volume", 0), errors="coerce").fillna(0) < 150_000
        ).astype(int)

    if "risk_extreme_volatility_flag" not in working_df.columns:
        volatility_proxy = pd.to_numeric(
            working_df.get("return_3m", 0),
            errors="coerce",
        ).abs().fillna(0)
        working_df["risk_extreme_volatility_flag"] = (volatility_proxy > 0.35).astype(int)

    return working_df


def rank_universe_dataframe(
    df: pd.DataFrame,
    top_n: int = 10,
    weights: ScoreWeights | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    enriched_df = _enrich_defaults(df)
    scored_df = score_universe(enriched_df, weights=weights)

    top_symbols = scored_df.head(top_n)["symbol"].astype(str).tolist()
    return scored_df, top_symbols


def rank_universe_from_csv(
    input_csv: str | Path,
    output_csv: str | Path,
    output_json: str | Path,
    top_n: int = 10,
    weights: ScoreWeights | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    source_df = _safe_read_csv(input_csv)
    scored_df, top_symbols = rank_universe_dataframe(
        source_df,
        top_n=top_n,
        weights=weights,
    )

    output_csv_path = Path(output_csv)
    output_json_path = Path(output_json)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    scored_df.to_csv(output_csv_path, index=False)

    with output_json_path.open("w", encoding="utf-8") as file:
        json.dump(top_symbols, file, ensure_ascii=False, indent=2)

    return scored_df, top_symbols
