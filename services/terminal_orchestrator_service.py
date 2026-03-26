from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_terminal_orchestration(
    *,
    market_overview: dict[str, Any] | None,
    ranking_available: bool,
    top_opportunities: list[dict[str, Any]] | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    execution_status: dict[str, Any] | None,
    skill_pipeline: dict[str, Any] | None = None,
    ai_analysis: dict[str, Any] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_symbols = symbol_payloads or {}
    normalized_trade_plans = trade_plan_payloads or {}
    normalized_execution = dict(execution_status or {})
    normalized_top_opportunities = top_opportunities or []
    normalized_ai = dict(ai_analysis or {})
    normalized_skill_pipeline = dict(skill_pipeline or {})

    stage_status = []
    pipeline_stages = normalized_skill_pipeline.get("stages")
    if isinstance(pipeline_stages, dict) and pipeline_stages:
        for name, payload in pipeline_stages.items():
            payload_dict = dict(payload) if isinstance(payload, dict) else {}
            stage_status.append(
                {
                    "name": str(name),
                    "enabled": str(payload_dict.get("status", "")).strip().lower() in {"ready", "proxy"},
                    "description": str(payload_dict.get("summary", "")).strip() or str(name),
                    "status": str(payload_dict.get("status", "missing")).strip().lower() or "missing",
                }
            )

    stages = [
        *stage_status,
        _stage("market_context", bool(normalized_market), "Market overview va breadth context"),
        _stage("ranking", ranking_available, "Universe ranking/scanner"),
        _stage("deep_dive", bool(normalized_symbols), "Phan tich chi tiet theo symbol"),
        _stage("trade_plan", bool(normalized_trade_plans), "Trade plan va action levels"),
        _stage("opportunity_selection", bool(normalized_top_opportunities), "Chon top opportunities"),
        _stage("ai_overlay", bool(normalized_ai), "Local/file/cloud AI overlay cho narrative"),
    ]

    completed = sum(1 for stage in stages if stage["enabled"])
    total = len(stages)
    quality = str(normalized_execution.get("quality", "unknown")).strip().lower() or "unknown"

    if quality == "healthy" and completed >= total - 1:
        mode = "full_stack"
    elif completed >= 3:
        mode = "analysis_ready"
    else:
        mode = "partial"

    return {
        "mode": mode,
        "completed_stages": completed,
        "total_stages": total,
        "stage_status": stages,
        "summary": _build_summary(mode, completed, total),
    }


def _stage(name: str, enabled: bool, description: str) -> DictStrAny:
    return {
        "name": name,
        "enabled": enabled,
        "description": description,
        "status": "ready" if enabled else "missing",
    }


def _build_summary(mode: str, completed: int, total: int) -> str:
    if mode == "full_stack":
        return f"Trading terminal da co du cac lop phan tich chinh ({completed}/{total} stages)."
    if mode == "analysis_ready":
        return f"Trading terminal co du bo canh de viet bai tong hop, nhung van con mot so lop du lieu thieu ({completed}/{total} stages)."
    return f"Trading terminal moi co mot phan bo context ({completed}/{total} stages), can them du lieu de narrative day hon."
