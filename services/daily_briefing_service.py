from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from services.analysis_critic_service import critique_analysis
from services.chief_analysis_writer_service import build_chief_analysis
from services.entry_execution_service import build_entry_execution_plan
from services.long_candidate_service import build_long_candidates
from services.market_brain_service import build_market_brain
from services.market_synthesis_service import build_market_synthesis
from services.news_impact_service import build_news_impact
from services.skill_pipeline_service import build_skill_pipeline_payload
from services.telegram_native_writer_service import build_telegram_native_brief
from services.terminal_orchestrator_service import build_terminal_orchestration
from services.vnindex_context_service import build_vnindex_context


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
    market_news_summary = _load_market_news_summary(PROJECT_ROOT)

    market_view = _build_market_view(selection_mode, normalized_market, normalized_warnings)
    execution_status = _build_execution_status(normalized_results, normalized_warnings)
    top_opportunities = _build_top_opportunities(
        ranking_table=normalized_ranking,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        symbol_results=normalized_results,
    )
    vnindex_context = build_vnindex_context(market_overview=normalized_market)
    news_impact = build_news_impact(
        market_news_summary=market_news_summary,
        symbol_payloads=normalized_symbols,
        warnings=normalized_warnings,
    )
    long_candidates = build_long_candidates(
        ranking_table=normalized_ranking,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
        top_n=5,
    )
    selected_longs = list(long_candidates.get("selected") or [])
    watchlist_only = list(long_candidates.get("watchlist_only") or [])
    top_opportunities = selected_longs
    entry_execution = build_entry_execution_plan(selected_candidates=selected_longs)
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
    market_brain = build_market_brain(
        market_synthesis=market_synthesis,
        chief_analysis=chief_analysis,
        long_candidates=long_candidates,
    )
    analysis_critic = critique_analysis(
        chief_analysis=chief_analysis,
    )
    telegram_native_brief = build_telegram_native_brief(
        run_id=run_id,
        chief_analysis=chief_analysis,
        market_brain=market_brain,
        analysis_critic=analysis_critic,
        long_candidates=long_candidates,
        entry_execution=entry_execution,
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
        "vnindex_context": vnindex_context,
        "news_impact": news_impact,
        "long_candidates": long_candidates,
        "entry_execution": entry_execution,
        "top_opportunities": top_opportunities,
        "watchlist_candidates": watchlist_only,
        "next_actions": next_actions,
        "warnings": normalized_warnings[:10],
        "skill_pipeline": skill_pipeline,
        "market_synthesis": market_synthesis,
        "chief_analysis": chief_analysis,
        "market_brain": market_brain,
        "analysis_critic": analysis_critic,
        "telegram_native_brief": telegram_native_brief,
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
        price_summary = _ensure_dict(analysis.get("price_summary"))
        day_change = _to_float(price_summary.get("day_change_pct"))
        period_change = _to_float(price_summary.get("period_change_pct"))
        setup_type = _string_or_none(plan.get("setup_type")) or "unknown"
        opportunities.append(
            {
                "symbol": symbol,
                "status": str(result.get("status", "unknown")),
                "setup_type": setup_type,
                "thesis": _string_or_none(plan.get("thesis")) or _string_or_none(analysis.get("thesis")) or "Cần đánh giá thêm trước khi hành động.",
                "trigger": _entry_zone_text(plan.get("entry_zone")),
                "invalidation": _string_or_none(plan.get("invalidation")) or "Chưa có điều kiện vô hiệu rõ ràng.",
                "risk_reward": _string_or_none(plan.get("risk_reward")) or "n/a",
                "degraded_mode": bool(plan.get("degraded_mode")) or bool(result.get("degraded_mode")),
                "day_change_pct": day_change,
                "period_change_pct": period_change,
                "long_case": _build_long_case(symbol=symbol, day_change=day_change, period_change=period_change, setup_type=setup_type),
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
    ordered: list[str] = []
    seen: set[str] = set()
    if not ranking_table.empty and "symbol" in ranking_table.columns:
        for symbol in ranking_table["symbol"].astype(str).str.strip().str.upper().tolist():
            if symbol and symbol not in seen:
                seen.add(symbol)
                ordered.append(symbol)
    for symbol in list(symbol_payloads.keys()) + list(trade_plan_payloads.keys()):
        normalized = str(symbol).strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _build_long_case(*, symbol: str, day_change: float | None, period_change: float | None, setup_type: str) -> str:
    day_text = _format_signed_pct(day_change)
    period_text = _format_signed_pct(period_change)
    action_text = {
        "pullback_buy": "phù hợp cho kịch bản LONG khi giá điều chỉnh về vùng theo dõi",
        "breakout_or_wait": "phù hợp cho kịch bản LONG nếu xuất hiện xác nhận bứt phá",
        "avoid_or_wait": "chưa phải ứng viên LONG ưu tiên, cần quan sát thêm",
        "unknown": "cần thêm xác nhận trước khi nâng lên kế hoạch LONG",
    }.get((setup_type or "unknown").lower(), "cần thêm xác nhận trước khi nâng lên kế hoạch LONG")
    parts = [f"{symbol} hiện {action_text}"]
    if day_text:
        parts.append(f"biến động phiên gần nhất {day_text}")
    if period_text:
        parts.append(f"xu hướng 3 tháng {period_text}")
    return "; ".join(parts) + "."


def _format_signed_pct(value: float | None) -> str:
    if value is None:
        return ""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _regime_text(value: str) -> str:
    mapping = {
        "risk_off": "thận trọng",
        "risk_on": "tích cực",
        "balanced": "cân bằng",
        "narrow_leadership": "phân hóa hẹp",
        "unknown": "chưa rõ",
    }
    return mapping.get(str(value).strip().lower(), str(value).strip().lower() or "chưa rõ")


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


def _load_market_news_summary(project_root: Path) -> DictStrAny:
    path = project_root / "data" / "derived" / "market_news_summary.json"
    if not path.exists():
        return {}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
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
