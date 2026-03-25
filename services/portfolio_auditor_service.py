from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_portfolio_audit(
    *,
    top_opportunities: list[dict[str, Any]] | None,
    risk_engine_payload: dict[str, Any] | None,
) -> DictStrAny:
    opportunities = [dict(item) for item in (top_opportunities or []) if isinstance(item, dict)]
    risk_payload = dict(risk_engine_payload or {})
    symbols = [str(item.get("symbol", "")).strip().upper() for item in opportunities if str(item.get("symbol", "")).strip()]
    high_risk = [row for row in risk_payload.get("rows", []) if isinstance(row, dict) and row.get("risk_tier") == "high"]

    posture = "balanced"
    if risk_payload.get("portfolio_risk") == "elevated":
        posture = "defensive"
    elif len(symbols) >= 3:
        posture = "selective offense"

    summary = f"Portfolio auditor đề xuất posture = {posture}."
    if high_risk:
        summary += f" Có {len(high_risk)} setup cần giảm size hoặc quan sát thêm."

    brief = build_analyst_brief(
        insight=f"Tư thế danh mục phù hợp hiện tại là {posture}.",
        evidence=[summary],
        implication="Danh mục nên ưu tiên ít vị thế nhưng có xác suất cao hơn là mở rộng dàn trải.",
        action=(f"Tập trung theo dõi {', '.join(symbols[:3])}." if symbols else "Giữ danh mục gọn và chờ thêm xác nhận."),
        risk="Nếu số setup rủi ro cao tăng lên, cần hạ mức cam kết vốn trên toàn danh mục.",
    )

    return {
        "status": "ready" if opportunities else "missing",
        "posture": posture,
        "summary": summary,
        "focus_symbols": symbols[:5],
        "analyst_brief": brief,
    }
