from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_market_internals_liquidity(
    *,
    market_overview: dict[str, Any] | None,
    ranking_rows: list[dict[str, Any]] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    rows = [dict(item) for item in (ranking_rows or []) if isinstance(item, dict)]
    breadth = _ensure_dict(normalized_market.get("breadth"))
    liquidity = _ensure_dict(normalized_market.get("liquidity_concentration"))

    advancers = _to_int(breadth.get("advancers"))
    decliners = _to_int(breadth.get("decliners"))
    positive_ratio = _to_float(breadth.get("positive_ratio"))
    share = _to_float(liquidity.get("top_n_liquidity_share"))
    top_symbols = []
    top_items = liquidity.get("top_symbols") if isinstance(liquidity.get("top_symbols"), list) else []
    for item in top_items[:10]:
        if isinstance(item, dict):
            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol:
                top_symbols.append(symbol)
    if not top_symbols:
        top_symbols = [str(row.get("symbol") or "").strip().upper() for row in rows[:10] if str(row.get("symbol") or "").strip()]

    health = "healthy" if (positive_ratio or 0) >= 0.5 and (share or 0) <= 0.5 else "narrow"
    explanation = (
        "Thị trường đang khỏe tương đối đồng đều, không chỉ dựa vào một vài mã trụ."
        if health == "healthy"
        else "Thị trường hiện có dấu hiệu kéo trụ hoặc tập trung thanh khoản vào nhóm hẹp; cần thận trọng với cảm giác xanh giả."
    )

    return {
        "status": "ready" if normalized_market else "degraded",
        "advance_decline": {"advancers": advancers, "decliners": decliners},
        "positive_ratio": positive_ratio,
        "liquidity_concentration": share,
        "top_index_contributors": top_symbols[:10],
        "health": health,
        "explanation": explanation,
        "analyst_brief": build_analyst_brief(
            insight=explanation,
            evidence=[f"A/D hiện tại: {advancers}/{decliners}.", f"Tỷ lệ mã tăng: {(positive_ratio or 0) * 100:.2f}%.", f"Mức tập trung thanh khoản: {(share or 0) * 100:.2f}%."],
            implication="Muốn xác nhận thị trường khỏe thật, cần thấy độ rộng cải thiện cùng lúc với việc thanh khoản bớt dồn vào một cụm quá hẹp.",
            action="Ưu tiên hành động khi breadth mở rộng và số mã dẫn dắt tăng lên, thay vì chỉ nhìn chỉ số tăng điểm.",
            risk="Nếu chỉ số xanh nhưng độ rộng vẫn yếu, khả năng cao đó mới là nhịp kéo trụ chứ chưa phải xu hướng bền.",
        ),
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


def _to_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0
