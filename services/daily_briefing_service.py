from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from services.chief_analysis_writer_service import build_chief_analysis
from services.market_synthesis_service import build_market_synthesis
from services.skill_pipeline_service import build_skill_pipeline_payload
from services.terminal_orchestrator_service import build_terminal_orchestration


DictStrAny = dict[str, Any]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    market_synthesis = build_market_synthesis(
        run_id=run_id,
        selection_mode=selection_mode,
        market_overview=normalized_market,
        ranking_table=normalized_ranking,
        top_opportunities=top_opportunities,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        execution_status=execution_status,
        warnings=normalized_warnings,
    )
    skill_pipeline = build_skill_pipeline_payload(
        project_root=PROJECT_ROOT,
        market_overview=normalized_market,
        ranking_table=normalized_ranking,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        top_opportunities=top_opportunities,
        warnings=normalized_warnings,
    )
    chief_analysis = build_chief_analysis(
        synthesis=market_synthesis,
        generated_at=run_id,
        skill_pipeline=skill_pipeline,
    )
    terminal_orchestration = build_terminal_orchestration(
        market_overview=normalized_market,
        ranking_available=not normalized_ranking.empty,
        top_opportunities=top_opportunities,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        execution_status=execution_status,
        skill_pipeline=skill_pipeline,
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
        "skill_pipeline": skill_pipeline,
        "market_synthesis": market_synthesis,
        "chief_analysis": chief_analysis,
        "terminal_orchestration": terminal_orchestration,
    }


def _build_market_view(selection_mode: str, market_overview: DictStrAny, warnings: list[str]) -> DictStrAny:
    regime = _ensure_dict(market_overview.get("regime"))
    breadth = _ensure_dict(market_overview.get("breadth"))
    index_context = _ensure_dict(market_overview.get("index_context"))

    if market_overview:
        summary = (
            _string_or_none(regime.get("explanation"))
            or _string_or_none(market_overview.get("summary"))
            or "Thị trường có dữ liệu overview, có thể dùng để đặt bối cảnh trước khi vào từng mã."
        )
    elif selection_mode == "watchlist":
        summary = "Run hiện đang ưu tiên watchlist để giảm tải request, vì vậy bối cảnh thị trường ở chế độ tối giản."
    else:
        summary = "Chưa tải được bối cảnh thị trường tổng quan, cần tham chiếu thêm khi ra quyết định."

    return {
        "summary": summary,
        "regime": _string_or_none(regime.get("regime")) or "unknown",
        "breadth": _string_or_none(breadth.get("status")) or "unknown",
        "volatility": _string_or_none(index_context.get("volatility")) or "unknown",
    }


def _build_execution_status(symbol_results: list[DictStrAny], warnings: list[str]) -> DictStrAny:
    total = len(symbol_results)
    success = sum(1 for item in symbol_results if str(item.get("status")) == "success")
    failed = sum(1 for item in symbol_results if str(item.get("status")) == "failed")
    degraded = sum(1 for item in symbol_results if bool(item.get("degraded_mode")))
    fallback_used = any(bool(item.get("fallback_used")) for item in symbol_results)

    quality = "healthy"
    if failed > 0:
        quality = "partial"
    elif degraded > 0 or warnings:
        quality = "degraded"

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
                "thesis": _string_or_none(plan.get("thesis")) or _string_or_none(analysis.get("thesis")) or "Cần review thêm trước khi hành động.",
                "trigger": _entry_zone_text(plan.get("entry_zone")),
                "invalidation": _string_or_none(plan.get("invalidation")) or "Chưa có invalidation rõ ràng.",
                "risk_reward": _string_or_none(plan.get("risk_reward")) or "n/a",
                "degraded_mode": bool(plan.get("degraded_mode")) or bool(result.get("degraded_mode")),
            }
        )

    return opportunities


def _build_next_actions(*, execution_status: DictStrAny, top_opportunities: list[DictStrAny], warnings: list[str]) -> list[str]:
    actions: list[str] = []
    quality = str(execution_status.get("quality", "unknown"))
    if quality == "healthy":
        actions.append("Ưu tiên review các setup có tỷ lệ lợi nhuận/rủi ro tốt và chỉ vào lệnh khi giá xác nhận quanh vùng theo dõi.")
    elif quality == "degraded":
        actions.append("Cần xem lại các cảnh báo degraded/fallback trước khi dùng báo cáo cho quyết định giao dịch thực tế.")
    else:
        actions.append("Báo cáo mới ở mức partial, ưu tiên kiểm tra các bước lỗi trước khi dùng cho quyết định giao dịch.")

    actionable_symbols = [item["symbol"] for item in top_opportunities if str(item.get("status")) == "success"]
    if actionable_symbols:
        actions.append(f"Tạo watchlist hành động cho: {', '.join(actionable_symbols[:3])}.")
    if any("rate limit" in warning.lower() for warning in warnings):
        actions.append("Nếu cần full scan trên cloud, cần API tier cao hơn hoặc self-hosted runner để tránh rate limit.")
    return actions[:5]


def _build_headline(market_view: DictStrAny, execution_status: DictStrAny, top_opportunities: list[DictStrAny]) -> str:
    first_symbol = top_opportunities[0]["symbol"] if top_opportunities else "watchlist"
    quality = str(execution_status.get("quality", "unknown"))
    regime = str(market_view.get("regime", "unknown"))
    if quality == "healthy":
        return f"Thị trường {regime}; ưu tiên chiến lược LONG có chọn lọc, theo dõi sát {first_symbol}."
    if quality == "degraded":
        return f"Pipeline ở chế độ degraded; dùng {first_symbol} như một ý tưởng cần review, không nên auto-trade."
    return f"Pipeline chưa hoàn chỉnh; cần review thủ công trước khi hành động với {first_symbol}."


def _ordered_symbols(ranking_table: pd.DataFrame, symbol_payloads: dict[str, DictStrAny], trade_plan_payloads: dict[str, DictStrAny]) -> list[str]:
    candidate_rows: list[tuple[float, str]] = []
    source_symbols: list[str] = []
    if not ranking_table.empty and "symbol" in ranking_table.columns:
        source_symbols.extend(ranking_table["symbol"].astype(str).str.strip().str.upper().tolist())
    source_symbols.extend(list(symbol_payloads.keys()))
    source_symbols.extend(list(trade_plan_payloads.keys()))

    seen: set[str] = set()
    for symbol in source_symbols:
        normalized = str(symbol).strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        analysis = symbol_payloads.get(normalized, {})
        plan = trade_plan_payloads.get(normalized, {})
        candidate_rows.append((_long_priority_score(normalized, ranking_table, analysis, plan), normalized))

    candidate_rows.sort(key=lambda item: item[0], reverse=True)
    return [symbol for _, symbol in candidate_rows]


def _long_priority_score(symbol: str, ranking_table: pd.DataFrame, analysis: DictStrAny, plan: DictStrAny) -> float:
    score = 0.0
    if not ranking_table.empty and "symbol" in ranking_table.columns:
        row_df = ranking_table[ranking_table["symbol"].astype(str).str.upper() == symbol]
        if not row_df.empty:
            row = row_df.iloc[0]
            score += float(pd.to_numeric(row.get("score", row.get("final_score")), errors="coerce") or 0.0) * 3
            score += float(pd.to_numeric(row.get("day_change_pct"), errors="coerce") or 0.0) * 2
            score += float(pd.to_numeric(row.get("return_3m"), errors="coerce") or 0.0) * 10
    price_summary = _ensure_dict(analysis.get("price_summary"))
    day_change = _to_float(price_summary.get("day_change_pct"))
    period_change = _to_float(price_summary.get("period_change_pct"))
    if day_change is not None:
        score += day_change * 2
        if day_change > 0:
            score += 8
        else:
            score -= 8
    if period_change is not None:
        score += period_change * 0.1
        if period_change > 0:
            score += 4
    setup_type = str(plan.get("setup_type", "")).strip().lower()
    thesis = str(plan.get("thesis", "")).strip().lower()
    if setup_type in {"pullback_buy", "breakout_or_wait"}:
        score += 8
    if setup_type == "avoid_or_wait":
        score -= 12
    if "downtrend" in thesis or "negative" in thesis:
        score -= 6
    if "uptrend" in thesis or "strong" in thesis:
        score += 4
    return score


def _entry_zone_text(entry_zone: Any) -> str:
    payload = _ensure_dict(entry_zone)
    low = payload.get("low")
    high = payload.get("high")
    strategy = _string_or_none(payload.get("strategy"))
    strategy_text = {"buy_on_pullback": "mua khi điều chỉnh", "staggered_entry": "giải ngân từng phần", "entry": "vào lệnh", "wait": "chờ"}.get((strategy or "").lower(), strategy or "theo dõi")
    if low is None and high is None:
        return strategy_text
    return f"{low} - {high} ({strategy_text})"


def _execution_summary_text(quality: str, total: int, success: int, degraded: int, failed: int) -> str:
    if quality == "healthy":
        return f"Pipeline ổn định: {success}/{total} mã đã có kết quả khả dụng."
    if quality == "degraded":
        return f"Pipeline degraded: {success}/{total} mã có kết quả, {degraded} mã đang ở chế độ fallback."
    return f"Pipeline partial: {failed} mã lỗi, cần review thủ công."


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
