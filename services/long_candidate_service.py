from __future__ import annotations

from typing import Any

import pandas as pd


DictStrAny = dict[str, Any]


def build_long_candidates(
    *,
    ranking_table: pd.DataFrame | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    top_n: int = 5,
) -> DictStrAny:
    ranking_df = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()
    symbol_data = {str(key).strip().upper(): dict(value) for key, value in (symbol_payloads or {}).items()}
    trade_data = {str(key).strip().upper(): dict(value) for key, value in (trade_plan_payloads or {}).items()}

    ranking_rows = _ranking_rows_by_symbol(ranking_df)
    symbols = _ordered_symbols(ranking_df, symbol_data, trade_data)
    candidates: list[DictStrAny] = []

    for symbol in symbols:
        analysis = symbol_data.get(symbol, {})
        plan = trade_data.get(symbol, {})
        price_summary = _ensure_dict(analysis.get("price_summary"))
        row = ranking_rows.get(symbol, {})

        day_change = _to_float(price_summary.get("day_change_pct"))
        period_change = _to_float(price_summary.get("period_change_pct"))
        last_close = _to_float(price_summary.get("last_close"))
        avg_volume = _to_float(price_summary.get("avg_volume")) or _to_float(row.get("avg_volume"))
        latest_volume = _to_float(price_summary.get("latest_volume"))
        volume_ratio = _safe_div(latest_volume, avg_volume) if latest_volume is not None and avg_volume not in {None, 0} else _to_float(row.get("volume_ratio_20d"))
        score = _to_float(row.get("final_score")) or _to_float(row.get("score")) or _to_float(row.get("raw_score")) or 0.0
        setup_type = str(plan.get("setup_type") or "unknown").strip().lower()
        risk_reward = _to_float(plan.get("risk_reward"))
        trend = str(plan.get("trend") or analysis.get("trend") or "").strip().lower()
        momentum = str(plan.get("momentum") or analysis.get("momentum") or "").strip().lower()
        news_summary = _ensure_dict(analysis.get("news_summary"))
        news_bonus = 0.3 if news_summary else 0.0

        long_score = 0.0
        reasons: list[str] = []

        if day_change is not None and day_change > 0:
            long_score += 2.0
            reasons.append(f"phiên gần nhất tăng {_fmt_pct(day_change)}")
        if period_change is not None and period_change > 0:
            long_score += 2.5
            reasons.append(f"xung lực 3 tháng đạt {_fmt_pct(period_change)}")
        if volume_ratio is not None and volume_ratio >= 1.0:
            long_score += 1.5
            reasons.append(f"khối lượng gần nhất tương đương {_fmt_num(volume_ratio, 2)} lần trung bình")
        if risk_reward is not None and risk_reward >= 2.0:
            long_score += 1.5
            reasons.append(f"RR tham chiếu ở mức {_fmt_num(risk_reward, 2)}")
        if setup_type == "pullback_buy":
            long_score += 2.0
            reasons.append("phù hợp kịch bản mua khi điều chỉnh")
        elif setup_type == "breakout_or_wait":
            long_score += 1.5
            reasons.append("có thể theo dõi cho kịch bản xác nhận bứt phá")
        if "up" in trend:
            long_score += 1.0
        if "strong" in momentum or "positive" in momentum:
            long_score += 1.0
        long_score += min(max(score, 0.0), 1.0) * 2.0
        long_score += news_bonus

        is_long_ready = (
            (day_change is not None and day_change > 0)
            and (period_change is not None and period_change > 0)
            and setup_type in {"pullback_buy", "breakout_or_wait"}
        )

        candidates.append(
            {
                "symbol": symbol,
                "is_long_ready": is_long_ready,
                "long_score": round(long_score, 4),
                "score": score,
                "day_change_pct": day_change,
                "period_change_pct": period_change,
                "volume_ratio": volume_ratio,
                "risk_reward": risk_reward,
                "last_close": last_close,
                "avg_volume": avg_volume,
                "setup_type": setup_type,
                "trigger": _entry_zone_text(plan.get("entry_zone")),
                "invalidation": str(plan.get("invalidation") or "").strip(),
                "thesis": str(plan.get("thesis") or analysis.get("thesis") or "").strip(),
                "selection_reasons": reasons[:4],
                "selection_note": _build_selection_note(symbol=symbol, reasons=reasons),
            }
        )

    candidates.sort(
        key=lambda item: (
            bool(item.get("is_long_ready")),
            float(item.get("long_score", 0.0)),
            _to_float(item.get("day_change_pct")) or -999.0,
            _to_float(item.get("period_change_pct")) or -999.0,
        ),
        reverse=True,
    )

    selected = [item for item in candidates if bool(item.get("is_long_ready"))][:top_n]
    fallback = candidates[:top_n] if len(selected) < top_n else []

    return {
        "status": "ready" if candidates else "missing",
        "selected": selected,
        "fallback_selected": fallback,
        "all_candidates": candidates[:15],
        "headline": _build_headline(selected),
        "selection_rule": "Ưu tiên mã tăng trong phiên, tăng trên chu kỳ theo dõi, có setup LONG rõ và RR đủ hấp dẫn.",
    }


def _build_headline(selected: list[DictStrAny]) -> str:
    if not selected:
        return "Chưa có đủ cổ phiếu đạt chuẩn LONG khỏe; cần tiếp tục quan sát thay vì ép chọn đủ số lượng."
    return "Top LONG hiện tại tập trung vào " + ", ".join(item["symbol"] for item in selected[:3]) + "."


def _build_selection_note(*, symbol: str, reasons: list[str]) -> str:
    if reasons:
        return f"{symbol} được giữ trong danh sách LONG vì " + "; ".join(reasons[:3]) + "."
    return f"{symbol} cần thêm dữ liệu xác nhận trước khi nâng thành ý tưởng LONG ưu tiên."


def _ranking_rows_by_symbol(df: pd.DataFrame) -> dict[str, DictStrAny]:
    if df.empty or "symbol" not in df.columns:
        return {}
    rows: dict[str, DictStrAny] = {}
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol:
            rows[symbol] = {str(key): row.get(key) for key in df.columns}
    return rows


def _ordered_symbols(ranking_df: pd.DataFrame, symbol_data: dict[str, DictStrAny], trade_data: dict[str, DictStrAny]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    if not ranking_df.empty and "symbol" in ranking_df.columns:
        for value in ranking_df["symbol"].astype(str).str.strip().str.upper().tolist():
            if value and value not in seen:
                seen.add(value)
                ordered.append(value)
    for source in [symbol_data, trade_data]:
        for symbol in source.keys():
            if symbol and symbol not in seen:
                seen.add(symbol)
                ordered.append(symbol)
    return ordered


def _entry_zone_text(entry_zone: Any) -> str:
    payload = _ensure_dict(entry_zone)
    low = payload.get("low")
    high = payload.get("high")
    strategy = str(payload.get("strategy") or "").strip().lower()
    strategy_map = {
        "buy_on_pullback": "mua khi điều chỉnh",
        "staggered_entry": "giải ngân từng phần",
        "entry": "vào lệnh",
        "wait": "chờ xác nhận",
    }
    strategy_text = strategy_map.get(strategy, strategy or "theo dõi")
    if low is None and high is None:
        return strategy_text
    return f"{low} - {high} ({strategy_text})"


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return numerator / denominator


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"
