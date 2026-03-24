from __future__ import annotations

from typing import Any

import pandas as pd


DictStrAny = dict[str, Any]


def build_stock_scanner_summary(ranking_table: pd.DataFrame | None) -> DictStrAny:
    df = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()
    if df.empty or "symbol" not in df.columns:
        return {
            "status": "missing",
            "summary": "Chua co bang ranking de scanner tong hop.",
            "top_symbols": [],
            "records": [],
        }

    records: list[DictStrAny] = []
    for _, row in df.head(10).iterrows():
        records.append(
            {
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "score": row.get("score", row.get("final_score")),
                "rank": row.get("rank"),
                "sector": row.get("sector", ""),
            }
        )

    symbols = [item["symbol"] for item in records if item.get("symbol")]
    summary = f"Scanner chon ra nhom uu tien: {', '.join(symbols[:5])}." if symbols else "Scanner chua co ket qua."

    return {
        "status": "ready",
        "summary": summary,
        "top_symbols": symbols[:10],
        "records": records,
    }
