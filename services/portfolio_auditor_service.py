from __future__ import annotations

from typing import Any


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

    summary = f"Portfolio auditor de xuat posture = {posture}."
    if high_risk:
        summary += f" Co {len(high_risk)} setup can giam size hoac quan sat them."

    return {
        "status": "ready" if opportunities else "missing",
        "posture": posture,
        "summary": summary,
        "focus_symbols": symbols[:5],
    }
