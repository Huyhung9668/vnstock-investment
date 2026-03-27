from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from services.execution_context_service import build_execution_context
from services.chart_pattern_lab_service import build_chart_pattern_lab
from services.deep_technical_lab_service import build_deep_technical_lab
from services.flow_of_funds_service import build_flow_of_funds
from services.foreign_flow_decoder_service import build_foreign_flow_decoder
from services.fundamental_profiler_service import build_fundamental_profiles
from services.futures_radar_service import build_futures_radar
from services.global_domestic_macro_lens_service import build_global_domestic_macro_lens
from services.entry_execution_service import build_entry_execution_plan
from services.long_candidate_service import build_long_candidates
from services.macro_context_service import build_macro_context
from services.market_internals_liquidity_service import build_market_internals_liquidity
from services.news_context_service import build_news_context
from services.news_impact_service import build_news_impact
from services.news_pressure_gauge_service import build_news_pressure_gauge
from services.order_engine_service import build_order_engine
from services.portfolio_auditor_service import build_portfolio_audit
from services.risk_engine_service import build_risk_engine
from services.scenario_engine_service import build_scenario_engine
from services.sector_strength_map_service import build_sector_strength_map
from services.stock_scanner_service import build_stock_scanner_summary
from services.technical_profiler_service import build_technical_profiles
from services.vnindex_context_service import build_vnindex_context
from services.vnindex_vn30_derivatives_state_service import build_vnindex_vn30_derivatives_state


DictStrAny = dict[str, Any]


def build_skill_pipeline_payload(
    *,
    project_root: Path,
    market_overview: dict[str, Any] | None,
    ranking_table: pd.DataFrame | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    top_opportunities: list[dict[str, Any]] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    market_news_summary = _load_json_if_exists(project_root / "data" / "derived" / "market_news_summary.json")
    ranking_rows = _dataframe_rows(ranking_table)

    scanner = build_stock_scanner_summary(ranking_table)
    macro_context = build_macro_context(
        market_overview=market_overview,
        market_news_summary=market_news_summary,
        warnings=warnings,
    )
    vnindex_context = build_vnindex_context(
        market_overview=market_overview,
    )
    news_context = build_news_context(
        market_news_summary=market_news_summary,
        symbol_payloads=symbol_payloads,
    )
    news_impact = build_news_impact(
        market_news_summary=market_news_summary,
        symbol_payloads=symbol_payloads,
        warnings=warnings,
    )
    futures_radar = build_futures_radar(
        market_overview=market_overview,
        warnings=warnings,
    )
    global_macro_lens = build_global_domestic_macro_lens(
        market_overview=market_overview,
        market_news_summary=market_news_summary,
        warnings=warnings,
    )
    derivatives_state = build_vnindex_vn30_derivatives_state(
        market_overview=market_overview,
        warnings=warnings,
    )
    flow_of_funds = build_flow_of_funds(
        market_overview=market_overview,
        ranking_rows=ranking_rows,
    )
    foreign_flow_decoder = build_foreign_flow_decoder(
        market_overview=market_overview,
        ranking_rows=ranking_rows,
        warnings=warnings,
    )
    sector_strength_map = build_sector_strength_map(
        ranking_table=ranking_table,
    )
    technical_profiles = build_technical_profiles(
        trade_plan_payloads=trade_plan_payloads,
    )
    long_candidates = build_long_candidates(
        ranking_table=ranking_table,
        symbol_payloads=symbol_payloads,
        trade_plan_payloads=trade_plan_payloads,
        top_n=5,
    )
    chart_pattern_lab = build_chart_pattern_lab(
        symbol_payloads=symbol_payloads,
        trade_plan_payloads=trade_plan_payloads,
    )
    deep_technical_lab = build_deep_technical_lab(
        symbol_payloads=symbol_payloads,
        trade_plan_payloads=trade_plan_payloads,
    )
    fundamental_profiles = build_fundamental_profiles(
        symbol_payloads=symbol_payloads,
    )
    risk_engine = build_risk_engine(
        trade_plan_payloads=trade_plan_payloads,
        warnings=warnings,
    )
    portfolio_audit = build_portfolio_audit(
        top_opportunities=top_opportunities,
        risk_engine_payload=risk_engine,
    )
    order_engine = build_order_engine(
        trade_plan_payloads=trade_plan_payloads,
        risk_engine_payload=risk_engine,
    )
    entry_execution = build_entry_execution_plan(
        selected_candidates=list(long_candidates.get("selected") or []),
    )
    market_internals = build_market_internals_liquidity(
        market_overview=market_overview,
        ranking_rows=ranking_rows,
    )
    news_pressure = build_news_pressure_gauge(
        market_news_summary=market_news_summary,
        warnings=warnings,
    )
    scenario_engine = build_scenario_engine(
        market_overview=market_overview,
        long_candidates=long_candidates,
        sector_strength=sector_strength_map,
    )
    execution_context = build_execution_context(
        trade_plan_payloads=trade_plan_payloads,
        risk_engine_payload=risk_engine,
        portfolio_audit_payload=portfolio_audit,
    )

    stages = {
        "macro_context": macro_context,
        "vnindex_context": vnindex_context,
        "news_context": news_context,
        "news_impact": news_impact,
        "futures_radar": futures_radar,
        "global_domestic_macro_lens": global_macro_lens,
        "vnindex_vn30_derivatives_state": derivatives_state,
        "flow_of_funds": flow_of_funds,
        "foreign_flow_decoder": foreign_flow_decoder,
        "sector_strength_map": sector_strength_map,
        "stock_scanner": scanner,
        "long_candidate_selector": long_candidates,
        "technical_profiler": technical_profiles,
        "deep_technical_lab": deep_technical_lab,
        "chart_pattern_lab": chart_pattern_lab,
        "fundamental_profiler": fundamental_profiles,
        "risk_engine": risk_engine,
        "portfolio_auditor": portfolio_audit,
        "order_engine": order_engine,
        "entry_execution": entry_execution,
        "market_internals_liquidity": market_internals,
        "news_pressure_gauge": news_pressure,
        "scenario_engine": scenario_engine,
        "execution_context": execution_context,
    }

    completed = sum(1 for value in stages.values() if str(value.get("status", "")).strip().lower() in {"ready", "proxy"})
    return {
        "status": "ready" if completed >= 6 else "partial",
        "completed_stage_count": completed,
        "total_stage_count": len(stages),
        "stages": stages,
    }


def _load_json_if_exists(path: Path) -> DictStrAny:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _dataframe_rows(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.head(20).fillna("").to_dict(orient="records")
