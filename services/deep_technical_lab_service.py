from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_deep_technical_lab(
    *,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
) -> DictStrAny:
    normalized_symbols = {str(key).strip().upper(): dict(value) for key, value in (symbol_payloads or {}).items()}
    normalized_plans = {str(key).strip().upper(): dict(value) for key, value in (trade_plan_payloads or {}).items()}
    rows: list[DictStrAny] = []

    for symbol, plan in normalized_plans.items():
        analysis = normalized_symbols.get(symbol, {})
        trend = _text(plan.get("trend") or analysis.get("trend") or "trung tính")
        momentum = _text(plan.get("momentum") or analysis.get("momentum") or "trung tính")
        setup_type = _text(plan.get("setup_type") or "unknown")
        risk_reward = _to_float(plan.get("risk_reward"))
        invalidation = _text(plan.get("invalidation"))
        entry_zone = _entry_zone_text(plan.get("entry_zone"))
        rows.append(
            {
                "symbol": symbol,
                "trend": trend,
                "momentum": momentum,
                "setup_type": setup_type,
                "risk_reward": risk_reward,
                "entry_zone": entry_zone,
                "invalidation": invalidation,
                "technical_state": _technical_state(trend=trend, momentum=momentum, risk_reward=risk_reward),
            }
        )

    rows.sort(key=lambda item: (item["technical_state"] == "constructive", item.get("risk_reward") or 0.0), reverse=True)
    lead = rows[0] if rows else {}

    return {
        "status": "ready" if rows else "degraded",
        "top_setups": rows[:5],
        "analyst_brief": build_analyst_brief(
            insight=(f"Lớp kỹ thuật chuyên sâu hiện ưu tiên {lead.get('symbol')} nhờ cấu trúc setup và tỷ lệ RR tương đối rõ." if lead else "Chưa có đủ dữ liệu để kết luận lớp kỹ thuật chuyên sâu."),
            evidence=[f"{item['symbol']}: {item['trend']} | {item['momentum']} | {item['entry_zone']}" for item in rows[:3]],
            implication="Chỉ báo kỹ thuật nên được đọc đa khung thời gian và gắn với vùng vô hiệu cụ thể trước khi vào lệnh.",
            action="Ưu tiên các setup constructive có vùng mua rõ, RR đủ tốt và chưa gãy cấu trúc hỗ trợ.",
            risk="Một setup kỹ thuật đẹp vẫn có thể thất bại nếu thị trường chung và dòng tiền không xác nhận.",
        ),
    }


def _technical_state(*, trend: str, momentum: str, risk_reward: float | None) -> str:
    text = f"{trend} {momentum}".lower()
    if any(token in text for token in ["up", "tăng", "strong", "positive", "tích cực"]) and (risk_reward or 0) >= 2.0:
        return "constructive"
    if any(token in text for token in ["down", "giảm", "weak", "negative", "tiêu cực"]):
        return "fragile"
    return "neutral"


def _entry_zone_text(entry_zone: Any) -> str:
    if isinstance(entry_zone, dict):
        low = entry_zone.get("low")
        high = entry_zone.get("high")
        strategy = _text(entry_zone.get("strategy")) or "theo dõi"
        if low is not None or high is not None:
            return f"{low} - {high} ({strategy})"
    return _text(entry_zone) or "chờ vùng mua rõ hơn"


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
