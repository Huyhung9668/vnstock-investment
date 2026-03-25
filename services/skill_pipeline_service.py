from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from services.execution_context_service import build_execution_context
from services.flow_of_funds_service import build_flow_of_funds
from services.fundamental_profiler_service import build_fundamental_profiles
from services.futures_radar_service import build_futures_radar
from services.macro_context_service import build_macro_context
from services.news_context_service import build_news_context
from services.portfolio_auditor_service import build_portfolio_audit
from services.risk_engine_service import build_risk_engine
from services.stock_scanner_service import build_stock_scanner_summary
from services.technical_profiler_service import build_technical_profiles


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
    news_context = build_news_context(
        market_news_summary=market_news_summary,
        symbol_payloads=symbol_payloads,
    )
    futures_radar = build_futures_radar(
        market_overview=market_overview,
        warnings=warnings,
    )
    flow_of_funds = build_flow_of_funds(
        market_overview=market_overview,
        ranking_rows=ranking_rows,
    )
    technical_profiles = build_technical_profiles(
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
    execution_context = build_execution_context(
        trade_plan_payloads=trade_plan_payloads,
        risk_engine_payload=risk_engine,
        portfolio_audit_payload=portfolio_audit,
    )

    stages = {
        "macro_context": macro_context,
        "news_context": news_context,
        "futures_radar": futures_radar,
        "flow_of_funds": flow_of_funds,
        "stock_scanner": scanner,
        "technical_profiler": technical_profiles,
        "fundamental_profiler": fundamental_profiles,
        "risk_engine": risk_engine,
        "portfolio_auditor": portfolio_audit,
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
