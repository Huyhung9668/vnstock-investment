from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_risk_engine(
    *,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    payloads = trade_plan_payloads or {}
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    rows: list[DictStrAny] = []
    for symbol, payload in sorted(payloads.items()):
        if not isinstance(payload, dict):
            continue
        degraded = bool(payload.get("degraded_mode"))
        risk_reward = payload.get("risk_reward")
        tier = "medium"
        if degraded:
            tier = "high"
        else:
            try:
                if risk_reward is not None and float(risk_reward) >= 1.5:
                    tier = "medium"
                elif risk_reward is not None and float(risk_reward) < 1.0:
                    tier = "high"
            except (TypeError, ValueError):
                tier = "medium"
        rows.append(
            {
                "symbol": str(symbol).strip().upper(),
                "risk_tier": tier,
                "degraded_mode": degraded,
                "risk_reward": risk_reward,
            }
        )

    portfolio_risk = "medium"
    if any(row["risk_tier"] == "high" for row in rows) or normalized_warnings:
        portfolio_risk = "elevated"

    return {
        "status": "ready" if rows else "missing",
        "portfolio_risk": portfolio_risk,
        "summary": f"Risk engine danh gia portfolio risk = {portfolio_risk}.",
        "rows": rows,
    }
