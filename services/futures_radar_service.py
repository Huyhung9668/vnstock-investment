from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_futures_radar(
    *,
    market_overview: dict[str, Any] | None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    regime = _ensure_dict(normalized_market.get("regime"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    ad_ratio = breadth.get("advance_decline_ratio")
    regime_name = str(regime.get("regime", "unknown")).strip().lower() or "unknown"

    bias = "neutral"
    note = "Chua co data phai sinh truc tiep, dang noi suy tu market breadth va regime."
    if regime_name == "risk_on":
        bias = "long_bias"
        note = "Boi canh nghiêng ve long bias, nhung can xac nhan them tu VN30F basis va OI."
    elif regime_name == "risk_off":
        bias = "short_bias"
        note = "Boi canh nghiêng ve short bias, uu tien phong thu neu khong co xac nhan dao chieu."

    if isinstance(ad_ratio, (int, float)) and ad_ratio < 0.9:
        bias = "short_bias"
    if any("degraded" in warning.lower() for warning in normalized_warnings):
        note += " Pipeline dang degraded nen futures radar chi mang tinh huong."

    return {
        "status": "proxy",
        "bias": bias,
        "note": note,
        "requires_live_futures_data": True,
    }


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}
