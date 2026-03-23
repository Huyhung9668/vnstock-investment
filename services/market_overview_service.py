from __future__ import annotations

from typing import Any

import pandas as pd


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def build_breadth_summary(df: pd.DataFrame) -> dict[str, Any]:
    working_df = df.copy()

    returns_3m = _safe_numeric(working_df["return_3m"]) if "return_3m" in working_df.columns else pd.Series(0.0, index=working_df.index)
    advancers = int((returns_3m > 0).sum())
    decliners = int((returns_3m < 0).sum())
    unchanged = int((returns_3m == 0).sum())
    total = int(len(working_df))

    advance_decline_ratio = advancers / decliners if decliners > 0 else float(advancers)
    positive_ratio = advancers / total if total > 0 else 0.0

    return {
        "total_symbols": total,
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advance_decline_ratio": round(advance_decline_ratio, 4),
        "positive_ratio": round(positive_ratio, 4),
    }


def build_sector_rotation(df: pd.DataFrame) -> list[dict[str, Any]]:
    working_df = df.copy()

    if "sector" not in working_df.columns:
        working_df["sector"] = "UNKNOWN"

    if "return_3m" not in working_df.columns:
        working_df["return_3m"] = 0.0

    if "avg_volume" not in working_df.columns:
        working_df["avg_volume"] = 0.0

    working_df["sector"] = working_df["sector"].astype(str).str.upper()
    working_df["return_3m"] = _safe_numeric(working_df["return_3m"])
    working_df["avg_volume"] = _safe_numeric(working_df["avg_volume"])

    grouped = (
        working_df.groupby("sector", dropna=False)
        .agg(
            symbol_count=("symbol", "count"),
            avg_return_3m=("return_3m", "mean"),
            avg_volume=("avg_volume", "mean"),
            total_volume=("avg_volume", "sum"),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        by=["avg_return_3m", "total_volume"],
        ascending=[False, False],
    ).reset_index(drop=True)

    grouped["rotation_label"] = grouped["avg_return_3m"].apply(
        lambda value: "leading" if value > 0.05 else ("lagging" if value < -0.05 else "neutral")
    )

    return grouped.to_dict(orient="records")


def build_liquidity_concentration(df: pd.DataFrame, top_n: int = 10) -> dict[str, Any]:
    working_df = df.copy()

    if "avg_volume" not in working_df.columns:
        working_df["avg_volume"] = 0.0

    working_df["avg_volume"] = _safe_numeric(working_df["avg_volume"])
    total_liquidity = float(working_df["avg_volume"].sum())

    if total_liquidity <= 0:
        return {
            "total_liquidity": 0.0,
            "top_n_liquidity_share": 0.0,
            "top_symbols": [],
        }

    top_df = working_df.sort_values(by="avg_volume", ascending=False).head(top_n).copy()
    top_liquidity = float(top_df["avg_volume"].sum())
    liquidity_share = top_liquidity / total_liquidity

    top_symbols = top_df[["symbol", "avg_volume"]].to_dict(orient="records")

    return {
        "total_liquidity": round(total_liquidity, 2),
        "top_n_liquidity_share": round(liquidity_share, 4),
        "top_symbols": top_symbols,
    }


def build_top_movers(df: pd.DataFrame, top_n: int = 10) -> dict[str, list[dict[str, Any]]]:
    working_df = df.copy()

    if "return_3m" not in working_df.columns:
        working_df["return_3m"] = 0.0

    if "exchange" not in working_df.columns:
        working_df["exchange"] = "UNKNOWN"

    if "sector" not in working_df.columns:
        working_df["sector"] = "UNKNOWN"

    if "avg_volume" not in working_df.columns:
        working_df["avg_volume"] = 0.0

    working_df["return_3m"] = _safe_numeric(working_df["return_3m"])
    working_df["avg_volume"] = _safe_numeric(working_df["avg_volume"])

    gainers = (
        working_df.sort_values(by=["return_3m", "avg_volume"], ascending=[False, False])
        .head(top_n)[["symbol", "exchange", "sector", "return_3m", "avg_volume"]]
        .to_dict(orient="records")
    )

    losers = (
        working_df.sort_values(by=["return_3m", "avg_volume"], ascending=[True, False])
        .head(top_n)[["symbol", "exchange", "sector", "return_3m", "avg_volume"]]
        .to_dict(orient="records")
    )

    return {
        "top_gainers": gainers,
        "top_losers": losers,
    }


def infer_market_regime(
    breadth_summary: dict[str, Any],
    sector_rotation: list[dict[str, Any]],
    liquidity_concentration: dict[str, Any],
) -> dict[str, Any]:
    positive_ratio = float(breadth_summary.get("positive_ratio", 0.0))
    ad_ratio = float(breadth_summary.get("advance_decline_ratio", 0.0))
    liquidity_share = float(liquidity_concentration.get("top_n_liquidity_share", 0.0))

    leading_sectors = sum(1 for row in sector_rotation if row.get("rotation_label") == "leading")
    lagging_sectors = sum(1 for row in sector_rotation if row.get("rotation_label") == "lagging")

    if positive_ratio >= 0.6 and ad_ratio > 1.2 and leading_sectors >= lagging_sectors:
        regime = "risk_on"
        explanation = "Độ rộng thị trường tích cực, số mã tăng chiếm ưu thế và nhóm ngành dẫn dắt mở rộng."
    elif positive_ratio <= 0.4 and ad_ratio < 0.8:
        regime = "risk_off"
        explanation = "Độ rộng thị trường yếu, bên giảm giá chiếm ưu thế và dòng tiền phòng thủ hơn."
    elif liquidity_share >= 0.45:
        regime = "narrow_leadership"
        explanation = "Dòng tiền tập trung mạnh vào một số ít mã dẫn dắt, độ lan tỏa chưa rộng."
    else:
        regime = "balanced"
        explanation = "Thị trường ở trạng thái cân bằng, chưa nghiêng rõ sang risk-on hoặc risk-off."

    return {
        "regime": regime,
        "explanation": explanation,
        "leading_sectors": leading_sectors,
        "lagging_sectors": lagging_sectors,
    }


def build_index_context(
    df: pd.DataFrame,
    regime_summary: dict[str, Any],
) -> dict[str, Any]:
    working_df = df.copy()

    avg_return_3m = float(_safe_numeric(working_df["return_3m"]).mean()) if "return_3m" in working_df.columns else 0.0
    median_return_3m = float(_safe_numeric(working_df["return_3m"]).median()) if "return_3m" in working_df.columns else 0.0
    avg_volume = float(_safe_numeric(working_df["avg_volume"]).mean()) if "avg_volume" in working_df.columns else 0.0

    return {
        "proxy_index": "universe_equal_weight_proxy",
        "avg_return_3m": round(avg_return_3m, 4),
        "median_return_3m": round(median_return_3m, 4),
        "avg_volume": round(avg_volume, 2),
        "regime": regime_summary.get("regime", "balanced"),
    }


def build_market_overview(df: pd.DataFrame) -> dict[str, Any]:
    breadth_summary = build_breadth_summary(df)
    sector_rotation = build_sector_rotation(df)
    liquidity_concentration = build_liquidity_concentration(df)
    top_movers = build_top_movers(df)
    regime_summary = infer_market_regime(
        breadth_summary=breadth_summary,
        sector_rotation=sector_rotation,
        liquidity_concentration=liquidity_concentration,
    )
    index_context = build_index_context(df, regime_summary=regime_summary)

    return {
        "breadth": breadth_summary,
        "sector_rotation": sector_rotation,
        "liquidity_concentration": liquidity_concentration,
        "top_movers": top_movers,
        "regime": regime_summary,
        "index_context": index_context,
    }
