from __future__ import annotations

from typing import Any

import pandas as pd

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_sector_strength_map(
    *,
    ranking_table: pd.DataFrame | None,
) -> DictStrAny:
    ranking_df = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()
    if ranking_df.empty or "symbol" not in ranking_df.columns:
        return {
            "status": "degraded",
            "leading": [],
            "improving": [],
            "weakening": [],
            "lagging": [],
            "analyst_brief": build_analyst_brief(
                insight="Chưa có đủ dữ liệu để xếp hạng sức mạnh ngành.",
                implication="Tạm thời nên đọc ngành theo hành vi giá của từng mã dẫn dắt.",
            ),
        }

    working = ranking_df.copy()
    if "sector" not in working.columns:
        working["sector"] = "UNKNOWN"
    working["sector"] = working["sector"].astype(str).str.strip().replace("", "UNKNOWN")
    working["relative_strength"] = _numeric_series(working, "return_3m") * 100
    working["breadth_proxy"] = (_numeric_series(working, "day_change_pct") > 0).astype(float)
    working["liquidity"] = _numeric_series(working, "volume_ratio_20d")
    working["foreign_flow_proxy"] = _numeric_series(working, "score", fallback="final_score")
    working["catalyst_proxy"] = _numeric_series(working, "news_signal")
    working["sector_score"] = (
        0.35 * working["relative_strength"]
        + 0.25 * working["breadth_proxy"] * 100
        + 0.20 * working["liquidity"] * 10
        + 0.10 * working["foreign_flow_proxy"] * 100
        + 0.10 * working["catalyst_proxy"] * 100
    )

    grouped = (
        working.groupby("sector", dropna=False)
        .agg(sector_score=("sector_score", "mean"), breadth=("breadth_proxy", "mean"), relative_strength=("relative_strength", "mean"))
        .reset_index()
        .sort_values("sector_score", ascending=False)
    )
    representatives = _representatives(working)
    rows = []
    for _, row in grouped.iterrows():
        sector = str(row.get("sector") or "UNKNOWN")
        score = float(row.get("sector_score") or 0.0)
        rows.append(
            {
                "sector": sector,
                "sector_score": round(score, 2),
                "state": _state_from_score(score),
                "relative_strength": round(float(row.get("relative_strength") or 0.0), 2),
                "breadth": round(float(row.get("breadth") or 0.0) * 100, 2),
                "representatives": representatives.get(sector, []),
            }
        )

    return {
        "status": "ready",
        "leading": [item for item in rows if item["state"] == "leading"][:5],
        "improving": [item for item in rows if item["state"] == "improving"][:5],
        "weakening": [item for item in rows if item["state"] == "weakening"][:5],
        "lagging": [item for item in rows if item["state"] == "lagging"][:5],
        "rows": rows[:12],
        "analyst_brief": build_analyst_brief(
            insight="Sức mạnh ngành nên được đọc bằng relative strength, breadth và độ mở rộng thanh khoản thay vì chỉ nhìn một vài mã kéo trụ.",
            evidence=[f"Nhóm dẫn đầu hiện tại: {', '.join(item['sector'] for item in rows[:3])}." if rows else "Chưa có ngành nổi trội rõ."],
            implication="Khi nhóm dẫn dắt mở rộng từ 1-2 cụm sang nhiều cụm, xác suất nhịp tăng bền sẽ cao hơn.",
            action="Ưu tiên chọn mã đại diện ở nhóm leading hoặc improving trước khi xem xét các nhóm lagging.",
            risk="Nếu điểm ngành phân hóa mạnh nhưng breadth toàn thị trường yếu, rủi ro kéo trụ rồi hụt hơi vẫn cao.",
        ),
    }


def _representatives(df: pd.DataFrame) -> dict[str, list[str]]:
    representatives: dict[str, list[str]] = {}
    sorted_df = df.sort_values(["sector_score", "symbol"], ascending=[False, True])
    for sector, group in sorted_df.groupby("sector", dropna=False):
        representatives[str(sector)] = group["symbol"].astype(str).str.upper().head(3).tolist()
    return representatives


def _state_from_score(score: float) -> str:
    if score >= 15:
        return "leading"
    if score >= 5:
        return "improving"
    if score <= -10:
        return "lagging"
    return "weakening"


def _numeric_series(df: pd.DataFrame, column: str, fallback: str | None = None) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    if fallback and fallback in df.columns:
        return pd.to_numeric(df[fallback], errors="coerce").fillna(0.0)
    return pd.Series(0.0, index=df.index)
