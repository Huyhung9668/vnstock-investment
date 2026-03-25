from __future__ import annotations

from typing import Any

import pandas as pd

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_stock_scanner_summary(ranking_table: pd.DataFrame | None) -> DictStrAny:
    df = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()
    if df.empty or "symbol" not in df.columns:
        return {
            "status": "missing",
            "summary": "Chưa có bảng ranking để scanner tổng hợp.",
            "top_symbols": [],
            "records": [],
            "analyst_brief": build_analyst_brief(
                insight="Scanner chưa đủ dữ liệu để xác định nhóm cổ phiếu ưu tiên.",
                implication="Cần hoàn tất bước xếp hạng trước khi nâng lên danh sách hành động.",
            ),
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
    summary = f"Scanner chọn ra nhóm ưu tiên: {', '.join(symbols[:5])}." if symbols else "Scanner chưa có kết quả."
    brief = build_analyst_brief(
        insight=(
            f"Nhóm cổ phiếu nổi bật hiện tại tập trung vào {', '.join(symbols[:3])}."
            if symbols else "Chưa có nhóm cổ phiếu nổi bật rõ ràng."
        ),
        evidence=[summary],
        implication="Danh sách này nên được xem là đầu vào cho bước technical, fundamental và execution thay vì là tín hiệu mua ngay.",
        action=(
            f"Ưu tiên đào sâu 3–5 mã đầu bảng để chọn ra ít ý tưởng nhưng chất lượng hơn."
        ),
        risk="Nếu top ranking thiếu độ đồng thuận giữa dòng tiền và xu hướng giá, tỷ lệ nhiễu sẽ cao.",
    )

    return {
        "status": "ready",
        "summary": summary,
        "top_symbols": symbols[:10],
        "records": records,
        "analyst_brief": brief,
    }
