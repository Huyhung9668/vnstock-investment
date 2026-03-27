from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_market_score(
    *,
    market_overview: dict[str, Any] | None,
    long_candidates: dict[str, Any] | None = None,
    sector_strength: dict[str, Any] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_longs = dict(long_candidates or {})
    normalized_sector = dict(sector_strength or {})

    regime = _ensure_dict(normalized_market.get("regime"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    liquidity = _ensure_dict(normalized_market.get("liquidity_concentration"))

    score = 50.0
    drivers: list[str] = []

    regime_name = str(regime.get("regime") or "").strip().lower()
    if regime_name == "risk_on":
        score += 15
        drivers.append("Regime thị trường nghiêng về risk-on.")
    elif regime_name == "risk_off":
        score -= 15
        drivers.append("Regime thị trường đang ở trạng thái risk-off.")

    positive_ratio = _to_float(breadth.get("positive_ratio"))
    if positive_ratio is not None:
        breadth_adj = (positive_ratio - 0.5) * 40
        score += breadth_adj
        drivers.append(f"Độ rộng điều chỉnh score khoảng {breadth_adj:.1f} điểm.")

    liquidity_share = _to_float(liquidity.get("top_n_liquidity_share"))
    if liquidity_share is not None:
        concentration_penalty = max(liquidity_share - 0.55, 0) * 20
        score -= concentration_penalty
        if concentration_penalty > 0:
            drivers.append(f"Thanh khoản tập trung hẹp làm giảm khoảng {concentration_penalty:.1f} điểm.")

    selected = [dict(item) for item in (normalized_longs.get("selected") or []) if isinstance(item, dict)]
    score += min(len(selected), 5) * 3
    if selected:
        drivers.append(f"Có {len(selected)} mã đạt chuẩn LONG nâng score ngắn hạn.")

    leading = [dict(item) for item in (normalized_sector.get("leading") or []) if isinstance(item, dict)]
    score += min(len(leading), 3) * 2
    if leading:
        drivers.append(f"Có {len(leading)} nhóm ngành dẫn dắt hỗ trợ độ lan tỏa.")

    score = max(0.0, min(100.0, score))
    bias = "bullish" if score >= 65 else "bearish" if score <= 40 else "neutral"

    return {
        "status": "ready",
        "score": round(score, 1),
        "bias": bias,
        "drivers": drivers[:5],
    }


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
