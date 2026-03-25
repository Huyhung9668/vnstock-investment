from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.analysis_package import AnalysisPackage


@dataclass(frozen=True)
class TradePlanContext:
    symbol: str
    current_price: float
    support: float | None
    resistance: float | None
    atr: float | None
    trend: str
    momentum: str
    catalysts: list[str]
    risks: list[str]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_nested(source: dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _extract_context(analysis: dict[str, Any]) -> TradePlanContext:
    symbol = str(analysis.get("symbol", "")).strip().upper() or "UNKNOWN"
    price_summary = _extract_nested(analysis, "price_summary") or {}
    breadth_context = _extract_nested(analysis, "breadth_context") or {}
    breadth_summary = _extract_nested(breadth_context, "breadth") or {}

    current_price = (
        _safe_float(analysis.get("current_price"))
        or _safe_float(analysis.get("last_price"))
        or _safe_float(_extract_nested(analysis, "price_summary", "current_price"))
        or _safe_float(_extract_nested(analysis, "price_summary", "last_price"))
        or _safe_float(_extract_nested(analysis, "price_summary", "last_close"))
        or _safe_float(price_summary.get("close"))
        or 0.0
    )

    support = (
        _safe_float(analysis.get("support"))
        or _safe_float(_extract_nested(analysis, "technical_summary", "support"))
        or _safe_float(_extract_nested(analysis, "trade_levels", "support"))
        or _safe_float(_infer_support_from_price_summary(price_summary, current_price))
    )

    resistance = (
        _safe_float(analysis.get("resistance"))
        or _safe_float(_extract_nested(analysis, "technical_summary", "resistance"))
        or _safe_float(_extract_nested(analysis, "trade_levels", "resistance"))
        or _safe_float(_infer_resistance_from_price_summary(price_summary, current_price))
    )

    atr = (
        _safe_float(analysis.get("atr"))
        or _safe_float(_extract_nested(analysis, "technical_summary", "atr"))
        or _safe_float(_extract_nested(analysis, "volatility", "atr"))
        or _safe_float(_infer_atr_from_price_summary(price_summary, current_price))
    )

    trend = str(
        analysis.get("trend")
        or _extract_nested(analysis, "technical_summary", "trend")
        or _infer_trend_from_price_summary(price_summary)
        or "neutral"
    ).strip().lower()

    momentum = str(
        analysis.get("momentum")
        or _extract_nested(analysis, "technical_summary", "momentum")
        or _infer_momentum_from_price_summary(price_summary)
        or "neutral"
    ).strip().lower()

    catalysts = (
        _safe_list(analysis.get("catalysts"))
        or _safe_list(_extract_nested(analysis, "news_summary", "catalyst_tags"))
        or _safe_list(_extract_nested(analysis, "news_summary", "catalysts"))
        or _market_context_catalysts(breadth_summary)
    )

    risks = (
        _safe_list(analysis.get("risks"))
        or _safe_list(_extract_nested(analysis, "news_summary", "risk_tags"))
        or _safe_list(_extract_nested(analysis, "risk_summary", "risk_tags"))
    )

    return TradePlanContext(
        symbol=symbol,
        current_price=current_price,
        support=support,
        resistance=resistance,
        atr=atr,
        trend=trend,
        momentum=momentum,
        catalysts=catalysts,
        risks=risks,
    )


def _infer_support_from_price_summary(price_summary: dict[str, Any], current_price: float) -> float | None:
    low_min = _safe_float(price_summary.get("low_min"))
    prev_close = _safe_float(price_summary.get("prev_close"))
    if low_min is not None and current_price > 0:
        support = max(low_min, current_price * 0.94)
        return round(min(support, current_price * 0.985), 2)
    if prev_close is not None and current_price > 0:
        return round(min(prev_close, current_price * 0.985), 2)
    return None


def _infer_resistance_from_price_summary(price_summary: dict[str, Any], current_price: float) -> float | None:
    high_max = _safe_float(price_summary.get("high_max"))
    if high_max is not None and current_price > 0:
        resistance = min(high_max, current_price * 1.1)
        if resistance > current_price:
            return round(resistance, 2)
    if current_price > 0:
        return round(current_price * 1.05, 2)
    return None


def _infer_atr_from_price_summary(price_summary: dict[str, Any], current_price: float) -> float | None:
    high_max = _safe_float(price_summary.get("high_max"))
    low_min = _safe_float(price_summary.get("low_min"))
    if high_max is not None and low_min is not None and high_max > low_min:
        return round((high_max - low_min) / 14.0, 2)
    if current_price > 0:
        return round(current_price * 0.03, 2)
    return None


def _infer_trend_from_price_summary(price_summary: dict[str, Any]) -> str | None:
    last_close = _safe_float(price_summary.get("last_close"))
    first_close = _safe_float(price_summary.get("first_close"))
    period_change_pct = _safe_float(price_summary.get("period_change_pct"))
    if period_change_pct is not None:
        if period_change_pct >= 10:
            return "uptrend"
        if period_change_pct <= -10:
            return "downtrend"
    if last_close is not None and first_close is not None:
        if last_close > first_close:
            return "uptrend"
        if last_close < first_close:
            return "downtrend"
    return None


def _infer_momentum_from_price_summary(price_summary: dict[str, Any]) -> str | None:
    day_change_pct = _safe_float(price_summary.get("day_change_pct"))
    period_change_pct = _safe_float(price_summary.get("period_change_pct"))
    if day_change_pct is not None:
        if day_change_pct >= 2:
            return "strong"
        if day_change_pct <= -2:
            return "weak"
    if period_change_pct is not None:
        if period_change_pct >= 5:
            return "positive"
        if period_change_pct <= -5:
            return "negative"
    return None


def _market_context_catalysts(breadth_summary: dict[str, Any]) -> list[str]:
    positive_ratio = _safe_float(breadth_summary.get("positive_ratio"))
    ad_ratio = _safe_float(breadth_summary.get("advance_decline_ratio"))
    catalysts: list[str] = []
    if positive_ratio is not None and positive_ratio >= 0.55:
        catalysts.append("Do rong thi truong dang ung ho ben mua")
    if ad_ratio is not None and ad_ratio >= 1.1:
        catalysts.append("Ty le advance/decline dang duy tri tren nguong tich cuc")
    return catalysts


def _infer_setup_type(context: TradePlanContext) -> str:
    if "up" in context.trend or "bull" in context.trend or "strong" in context.momentum:
        return "pullback_buy"
    if "down" in context.trend or "bear" in context.trend:
        return "avoid_or_wait"
    return "breakout_or_wait"


def _build_thesis(context: TradePlanContext) -> str:
    parts: list[str] = []

    if context.trend not in {"", "neutral"}:
        parts.append(f"Xu hướng hiện tại nghiêng về {context.trend}.")
    else:
        parts.append("Xu hướng hiện tại chưa thật sự rõ ràng.")

    if context.momentum not in {"", "neutral"}:
        parts.append(f"Động lượng đang ở trạng thái {context.momentum}.")

    if context.catalysts:
        parts.append(f"Catalyst đáng chú ý: {', '.join(context.catalysts[:3])}.")

    if context.risks:
        parts.append(f"Rủi ro cần theo dõi: {', '.join(context.risks[:3])}.")

    return " ".join(parts).strip()


def _fallback_stop_pct(context: TradePlanContext) -> float:
    if context.current_price <= 0:
        return 0.0
    if "strong" in context.momentum:
        return context.current_price * 0.05
    if "down" in context.trend:
        return context.current_price * 0.03
    return context.current_price * 0.04


def _build_entry_zone(context: TradePlanContext) -> dict[str, Any]:
    price = context.current_price

    if price <= 0:
        return {
            "low": None,
            "high": None,
            "strategy": "wait",
            "rationale": "Thiếu current_price nên chưa thể xác định entry zone đáng tin cậy.",
        }

    if context.support is not None:
        low = round(context.support * 1.00, 2)
        high = round(max(context.support * 1.02, low), 2)
        return {
            "low": low,
            "high": high,
            "strategy": "buy_on_pullback",
            "rationale": "Ưu tiên mua khi giá lùi về vùng hỗ trợ thay vì đuổi giá.",
        }

    low = round(price * 0.98, 2)
    high = round(price * 1.01, 2)
    return {
        "low": low,
        "high": high,
        "strategy": "staggered_entry",
        "rationale": "Không có hỗ trợ rõ ràng, dùng vùng quanh giá hiện tại với giải ngân từng phần.",
    }


def _build_confirmation(context: TradePlanContext, entry_zone: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    if entry_zone.get("strategy") == "buy_on_pullback":
        checks.append("Giá phản ứng tích cực tại vùng entry và không thủng hỗ trợ trong phiên.")
    else:
        checks.append("Giá đóng cửa giữ trên vùng entry sau khi giải ngân thăm dò.")

    if context.resistance is not None:
        checks.append(f"Ưu tiên khi giá vượt/giữ được trên vùng cản gần {round(context.resistance, 2)}.")

    if "strong" in context.momentum or "up" in context.trend:
        checks.append("Thanh khoản duy trì tích cực, không suy yếu rõ rệt so với các phiên gần nhất.")

    if context.catalysts:
        checks.append("Catalyst ngắn hạn vẫn còn hiệu lực, không bị phủ định bởi tin mới.")

    return checks


def _build_invalidation(context: TradePlanContext, entry_zone: dict[str, Any]) -> str:
    if context.support is not None:
        return f"Thesis bị vô hiệu nếu giá thủng rõ ràng vùng hỗ trợ {round(context.support, 2)} với áp lực bán tăng."
    if entry_zone.get("low") is not None:
        return f"Thesis bị vô hiệu nếu giá thủng vùng entry thấp {entry_zone['low']} và không hồi phục."
    return "Thesis bị vô hiệu nếu cấu trúc giá xấu đi và động lượng chuyển sang tiêu cực."


def _build_stop_loss(context: TradePlanContext, entry_zone: dict[str, Any]) -> float | None:
    if context.current_price <= 0:
        return None

    if context.atr is not None and context.atr > 0:
        reference = context.support if context.support is not None else context.current_price
        return round(reference - context.atr, 2)

    if context.support is not None:
        return round(context.support * 0.98, 2)

    fallback_gap = _fallback_stop_pct(context)
    return round(context.current_price - fallback_gap, 2)


def _build_target(context: TradePlanContext, entry_zone: dict[str, Any], stop_loss: float | None) -> dict[str, Any]:
    entry_high = _safe_float(entry_zone.get("high"))
    entry_ref = entry_high or context.current_price

    if entry_ref is None or entry_ref <= 0:
        return {"target_1": None, "target_2": None, "rationale": "Thiếu dữ liệu để xác định target."}

    if context.resistance is not None and context.resistance > entry_ref:
        target_1 = round(context.resistance, 2)
    else:
        target_1 = round(entry_ref * 1.08, 2)

    if stop_loss is not None and entry_ref > stop_loss:
        risk_per_share = entry_ref - stop_loss
        target_2 = round(entry_ref + risk_per_share * 2.0, 2)
    else:
        target_2 = round(entry_ref * 1.12, 2)

    return {
        "target_1": target_1,
        "target_2": target_2,
        "rationale": "Ưu tiên chốt một phần ở cản gần, phần còn lại theo risk-reward mở rộng.",
    }


def _build_risk_reward(entry_zone: dict[str, Any], stop_loss: float | None, target: dict[str, Any]) -> float | None:
    entry_ref = _safe_float(entry_zone.get("high")) or _safe_float(entry_zone.get("low"))
    target_1 = _safe_float(target.get("target_1"))

    if entry_ref is None or stop_loss is None or target_1 is None:
        return None

    risk = entry_ref - stop_loss
    reward = target_1 - entry_ref

    if risk <= 0:
        return None

    return round(reward / risk, 2)


def _build_position_sizing_hint(context: TradePlanContext, risk_reward: float | None) -> str:
    if context.risks:
        return "Giảm quy mô vị thế, ưu tiên thăm dò 25%–33% size chuẩn do còn risk tags."
    if risk_reward is not None and risk_reward >= 1.5:
        return "Có thể vào 2 nhịp: 50% vị thế thăm dò, 50% còn lại khi có xác nhận."
    return "Ưu tiên vị thế nhỏ đến trung bình, giải ngân từng phần thay vì vào đủ ngay."


def _build_monitoring_checklist(context: TradePlanContext, target: dict[str, Any]) -> list[str]:
    checks = [
        "Theo dõi phản ứng giá quanh vùng entry.",
        "Theo dõi thanh khoản so với trung bình 20 phiên.",
        "Kiểm tra thị trường chung có duy trì regime thuận lợi hay không.",
    ]

    if context.catalysts:
        checks.append("Theo dõi tin mới để xác nhận catalyst còn hiệu lực.")

    if context.risks:
        checks.append("Theo dõi các risk tags xem có diễn biến xấu thêm không.")

    if target.get("target_1") is not None:
        checks.append(f"Cân nhắc chốt một phần khi tiệm cận target 1 = {target['target_1']}.")

    return checks


def _format_scalar(value: Any) -> str:
    if value is None:
        return "Chưa có dữ liệu"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_list(values: list[str]) -> list[str]:
    if not values:
        return ["- Chưa có dữ liệu bổ sung."]
    return [f"- {item}" for item in values]


def generate_trade_plan(analysis: dict[str, Any]) -> dict[str, Any]:
    context = _extract_context(analysis)

    entry_zone = _build_entry_zone(context)
    stop_loss = _build_stop_loss(context, entry_zone)
    target = _build_target(context, entry_zone, stop_loss)
    risk_reward = _build_risk_reward(entry_zone, stop_loss, target)

    notes: list[str] = []
    degraded_mode = False

    if context.current_price <= 0:
        degraded_mode = True
        notes.append("Thiếu current_price đáng tin cậy.")
    if context.support is None:
        notes.append("Thiếu support rõ ràng, entry/stop dùng fallback.")
    if context.resistance is None:
        notes.append("Thiếu resistance rõ ràng, target dùng heuristic.")
    if context.atr is None:
        notes.append("Thiếu ATR, stop loss dùng rule theo %.")

    return {
        "symbol": context.symbol,
        "setup_type": _infer_setup_type(context),
        "thesis": _build_thesis(context),
        "entry_zone": entry_zone,
        "confirmation": _build_confirmation(context, entry_zone),
        "invalidation": _build_invalidation(context, entry_zone),
        "target": target,
        "stop_loss": stop_loss,
        "risk_reward": risk_reward,
        "position_sizing_hint": _build_position_sizing_hint(context, risk_reward),
        "monitoring_checklist": _build_monitoring_checklist(context, target),
        "notes": notes,
        "degraded_mode": degraded_mode,
    }


def render_trade_plan(package: AnalysisPackage) -> str:
    analysis = package.to_dict() if hasattr(package, "to_dict") else {}
    plan = generate_trade_plan(analysis)

    entry_zone = plan.get("entry_zone", {})
    target = plan.get("target", {})
    confirmation = plan.get("confirmation", [])
    monitoring = plan.get("monitoring_checklist", [])
    notes = plan.get("notes", [])

    lines = [
        f"# Trade Plan: {plan.get('symbol', package.symbol)}",
        "",
        f"- Thesis: {plan.get('thesis', 'Chưa có dữ liệu')}",
        f"- Setup type: {plan.get('setup_type', 'unknown')}",
        (
            "- Entry zone: "
            f"{_format_scalar(entry_zone.get('low'))} - {_format_scalar(entry_zone.get('high'))}"
        ),
        f"- Confirmation: {'; '.join(str(item) for item in confirmation) if confirmation else 'Chưa có dữ liệu'}",
        f"- Invalidation: {plan.get('invalidation', 'Chưa có dữ liệu')}",
        (
            "- Target: "
            f"T1={_format_scalar(target.get('target_1'))}, "
            f"T2={_format_scalar(target.get('target_2'))}"
        ),
        f"- Stop loss: {_format_scalar(plan.get('stop_loss'))}",
        f"- Risk reward: {_format_scalar(plan.get('risk_reward'))}",
        f"- Position sizing hint: {plan.get('position_sizing_hint', 'Chưa có dữ liệu')}",
        f"- Degraded mode: {'true' if bool(plan.get('degraded_mode', False)) else 'false'}",
        "",
        "## Monitoring checklist",
        *_format_list([str(item) for item in monitoring]),
        "",
        "## Notes",
        *_format_list([str(item) for item in notes]),
    ]

    return "\n".join(lines) + "\n"
