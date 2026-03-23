from __future__ import annotations

from typing import Any

import pandas as pd


DictStrAny = dict[str, Any]


def build_daily_briefing(
    *,
    run_id: str,
    selection_mode: str,
    market_overview: dict[str, Any] | None,
    ranking_table: pd.DataFrame | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    symbol_results: list[dict[str, Any]] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_symbols = {str(key).strip().upper(): dict(value) for key, value in (symbol_payloads or {}).items()}
    normalized_trade_plans = {
        str(key).strip().upper(): dict(value) for key, value in (trade_plan_payloads or {}).items()
    }
    normalized_results = [dict(item) for item in (symbol_results or []) if isinstance(item, dict)]
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    normalized_ranking = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()

    market_view = _build_market_view(selection_mode, normalized_market, normalized_warnings)
    execution_status = _build_execution_status(normalized_results, normalized_warnings)
    top_opportunities = _build_top_opportunities(
        ranking_table=normalized_ranking,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        symbol_results=normalized_results,
    )
    next_actions = _build_next_actions(
        execution_status=execution_status,
        top_opportunities=top_opportunities,
        warnings=normalized_warnings,
    )

    return {
        "run_id": run_id,
        "headline": _build_headline(market_view, execution_status, top_opportunities),
        "selection_mode": selection_mode,
        "market_view": market_view,
        "execution_status": execution_status,
        "top_opportunities": top_opportunities,
        "next_actions": next_actions,
        "warnings": normalized_warnings[:10],
    }


def _build_market_view(selection_mode: str, market_overview: DictStrAny, warnings: list[str]) -> DictStrAny:
    regime = _ensure_dict(market_overview.get("regime"))
    breadth = _ensure_dict(market_overview.get("breadth"))
    index_context = _ensure_dict(market_overview.get("index_context"))

    if market_overview:
        summary = (
            _string_or_none(regime.get("explanation"))
            or _string_or_none(market_overview.get("summary"))
            or "Thi truong co du lieu overview, co the dung de dat boi canh truoc khi vao tung ma."
        )
    elif selection_mode == "watchlist":
        summary = "CI run dang uu tien watchlist de giam tai request, vi vay boi canh thi truong dang o che do toi gian."
    else:
        summary = "Chua tai duoc boi canh thi truong tong quan, can tham chieu them khi ra quyet dinh."

    return {
        "summary": summary,
        "regime": _string_or_none(regime.get("regime")) or "unknown",
        "breadth": _string_or_none(breadth.get("market_breadth")) or "unknown",
        "volatility": _string_or_none(index_context.get("volatility")) or "unknown",
        "degraded": not bool(market_overview),
        "warning_count": len(warnings),
    }


def _build_execution_status(symbol_results: list[DictStrAny], warnings: list[str]) -> DictStrAny:
    total = len(symbol_results)
    success = sum(1 for item in symbol_results if str(item.get("status")) == "success")
    degraded = sum(1 for item in symbol_results if bool(item.get("degraded_mode")))
    failed = sum(1 for item in symbol_results if str(item.get("status")) == "failed")
    fallback_used = any(bool(item.get("fallback_used")) for item in symbol_results)

    if failed > 0:
        quality = "partial"
    elif degraded > 0 or fallback_used or warnings:
        quality = "degraded"
    else:
        quality = "healthy"

    return {
        "quality": quality,
        "total_symbols": total,
        "success_symbols": success,
        "failed_symbols": failed,
        "degraded_symbols": degraded,
        "fallback_used": fallback_used,
        "summary": _execution_summary_text(quality, total, success, degraded, failed),
    }


def _build_top_opportunities(
    *,
    ranking_table: pd.DataFrame,
    symbol_payloads: dict[str, DictStrAny],
    trade_plan_payloads: dict[str, DictStrAny],
    symbol_results: list[DictStrAny],
) -> list[DictStrAny]:
    ordered_symbols = _ordered_symbols(ranking_table, symbol_payloads, trade_plan_payloads)
    results_by_symbol = {str(item.get("symbol", "")).strip().upper(): item for item in symbol_results}
    opportunities: list[DictStrAny] = []

    for symbol in ordered_symbols[:5]:
        analysis = symbol_payloads.get(symbol, {})
        plan = trade_plan_payloads.get(symbol, {})
        result = results_by_symbol.get(symbol, {})
        opportunities.append(
            {
                "symbol": symbol,
                "status": str(result.get("status", "unknown")),
                "setup_type": _string_or_none(plan.get("setup_type")) or "unknown",
                "thesis": _string_or_none(plan.get("thesis")) or _string_or_none(analysis.get("thesis")) or "Can review them truoc khi hanh dong.",
                "trigger": _entry_zone_text(plan.get("entry_zone")),
                "invalidation": _string_or_none(plan.get("invalidation")) or "Chua co invalidation ro rang.",
                "risk_reward": _string_or_none(plan.get("risk_reward")) or "n/a",
                "degraded_mode": bool(plan.get("degraded_mode")) or bool(result.get("degraded_mode")),
            }
        )

    return opportunities


def _build_next_actions(
    *,
    execution_status: DictStrAny,
    top_opportunities: list[DictStrAny],
    warnings: list[str],
) -> list[str]:
    actions: list[str] = []

    quality = str(execution_status.get("quality", "unknown"))
    if quality == "healthy":
        actions.append("Uu tien review cac setup co risk_reward on va lenh xac nhan quanh entry zone.")
    elif quality == "degraded":
        actions.append("Can xem lai cac canh bao degraded/fallback truoc khi dung bao cao de vao lenh that.")
    else:
        actions.append("Bao cao moi o muc partial, uu tien kiem tra cac buoc loi truoc khi dung cho quyet dinh giao dich.")

    degraded_symbols = [item["symbol"] for item in top_opportunities if bool(item.get("degraded_mode"))]
    if degraded_symbols:
        actions.append(f"Review thu cong du lieu cho: {', '.join(degraded_symbols[:3])}.")

    actionable_symbols = [item["symbol"] for item in top_opportunities if str(item.get("status")) == "success"]
    if actionable_symbols:
        actions.append(f"Tao watchlist hanh dong cho: {', '.join(actionable_symbols[:3])}.")

    if any("rate limit" in warning.lower() for warning in warnings):
        actions.append("Neu can full scan tren cloud, can API tier cao hon hoac self-hosted runner de tranh rate limit.")

    if not actions:
        actions.append("Khong co hanh dong noi bat. Tiep tuc giam sat va cho du lieu xac nhan them.")

    return actions[:5]


def _build_headline(
    market_view: DictStrAny,
    execution_status: DictStrAny,
    top_opportunities: list[DictStrAny],
) -> str:
    first_symbol = top_opportunities[0]["symbol"] if top_opportunities else "watchlist"
    quality = str(execution_status.get("quality", "unknown"))
    regime = str(market_view.get("regime", "unknown"))
    if quality == "healthy":
        return f"Thi truong {regime}; uu tien hanh dong tren {first_symbol} neu setup duoc xac nhan."
    if quality == "degraded":
        return f"Pipeline o che do degraded; dung {first_symbol} nhu mot y tuong can review, khong nen auto-trade."
    return f"Pipeline chua hoan chinh; can review thu cong truoc khi hanh dong voi {first_symbol}."


def _ordered_symbols(
    ranking_table: pd.DataFrame,
    symbol_payloads: dict[str, DictStrAny],
    trade_plan_payloads: dict[str, DictStrAny],
) -> list[str]:
    ordered: list[str] = []
    if not ranking_table.empty and "symbol" in ranking_table.columns:
        for symbol in ranking_table["symbol"].astype(str).tolist():
            normalized = symbol.strip().upper()
            if normalized and normalized not in ordered:
                ordered.append(normalized)

    for symbol in list(symbol_payloads.keys()) + list(trade_plan_payloads.keys()):
        if symbol and symbol not in ordered:
            ordered.append(symbol)

    return ordered


def _entry_zone_text(entry_zone: Any) -> str:
    payload = _ensure_dict(entry_zone)
    low = payload.get("low")
    high = payload.get("high")
    strategy = _string_or_none(payload.get("strategy"))
    if low is None and high is None:
        return strategy or "wait"
    return f"{low} - {high} ({strategy or 'entry'})"


def _execution_summary_text(quality: str, total: int, success: int, degraded: int, failed: int) -> str:
    if quality == "healthy":
        return f"Pipeline on dinh: {success}/{total} symbol da co ket qua kha dung."
    if quality == "degraded":
        return f"Pipeline degraded: {success}/{total} symbol co ket qua, {degraded} symbol dang o che do fallback."
    return f"Pipeline partial: {failed} symbol loi, can review thu cong."


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
