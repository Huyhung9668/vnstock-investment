from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.agent_planner_service import build_agent_plan
from services.agent_skill_loader_service import load_skill_metadata_map
from services.agent_skill_runtime import AgentRuntimeContext, AgentSkill, AgentStepResult, SkillMetadata
from services.quality_gates_service import run_quality_gates
from services.source_health_service import check_source_health


DictStrAny = dict[str, Any]


def build_skill_registry(*, project_root: Path) -> dict[str, AgentSkill]:
    skill_root = project_root / ".agents" / "skills"
    metadata_map = load_skill_metadata_map(skill_root)

    def meta(name: str, fallback_description: str) -> SkillMetadata:
        return metadata_map.get(name) or SkillMetadata(name=name, description=fallback_description)

    return {
        "env_setup": AgentSkill(
            skill_id="env_setup",
            metadata=meta("10-vnstock-env-setup", "Load runtime bundle and initialize agent context."),
            handler=_env_setup,
            produces=["runtime_bundle", "run_context"],
        ),
        "source_health": AgentSkill(
            skill_id="source_health",
            metadata=meta("13-source-registry", "Check source readiness and fallback state."),
            handler=_source_health,
            depends_on=["env_setup"],
            produces=["source_health"],
        ),
        "market_overview": AgentSkill(
            skill_id="market_overview",
            metadata=meta("31-market-radar", "Load market overview and internal breadth state."),
            handler=_market_overview,
            depends_on=["env_setup"],
            produces=["market_overview"],
        ),
        "ranking_selection": AgentSkill(
            skill_id="ranking_selection",
            metadata=meta("40-stock-scanner", "Rank candidates and select top symbols."),
            handler=_ranking_selection,
            depends_on=["env_setup"],
            produces=["ranking_table", "selected_symbols"],
        ),
        "deep_dive": AgentSkill(
            skill_id="deep_dive",
            metadata=meta("41-technical-profiler", "Build deep dives for selected symbols."),
            handler=_deep_dive,
            depends_on=["ranking_selection"],
            produces=["deep_dives"],
        ),
        "trade_plan": AgentSkill(
            skill_id="trade_plan",
            metadata=meta("52-order-engine", "Generate trade plans from deep dives."),
            handler=_trade_plan,
            depends_on=["deep_dive"],
            produces=["trade_plans"],
        ),
        "daily_briefing": AgentSkill(
            skill_id="daily_briefing",
            metadata=meta("70-market-synthesis", "Compose full daily briefing payload."),
            handler=_daily_briefing,
            depends_on=["market_overview", "trade_plan"],
            produces=["daily_briefing"],
        ),
        "vnindex_context": AgentSkill(
            skill_id="vnindex_context",
            metadata=meta("31-market-radar", "Extract VNINDEX-style market context."),
            handler=_extract_vnindex_context,
            depends_on=["daily_briefing"],
            produces=["vnindex_context"],
        ),
        "news_impact": AgentSkill(
            skill_id="news_impact",
            metadata=meta("20-news-crawler", "Extract news impact layer."),
            handler=_extract_news_impact,
            depends_on=["daily_briefing"],
            produces=["news_impact"],
        ),
        "long_candidate_selector": AgentSkill(
            skill_id="long_candidate_selector",
            metadata=meta("44-long-candidate-selector", "Extract top long candidates."),
            handler=_extract_long_candidates,
            depends_on=["daily_briefing"],
            produces=["long_candidates"],
        ),
        "entry_execution": AgentSkill(
            skill_id="entry_execution",
            metadata=meta("54-entry-scaling-playbook", "Extract staged entry execution plan."),
            handler=_extract_entry_execution,
            depends_on=["daily_briefing"],
            produces=["entry_execution"],
        ),
        "quality_gates": AgentSkill(
            skill_id="quality_gates",
            metadata=meta("22-data-guardian", "Run final quality gates on aggregated payload."),
            handler=_quality_gates,
            depends_on=["daily_briefing"],
            produces=["quality_gates"],
        ),
        "export_reports": AgentSkill(
            skill_id="export_reports",
            metadata=meta("63-dashboard-publisher", "Export report bundle and artifacts."),
            handler=_export_reports,
            depends_on=["daily_briefing"],
            produces=["bundle_output_dir"],
        ),
        "write_manifest": AgentSkill(
            skill_id="write_manifest",
            metadata=meta("63-dashboard-publisher", "Write final manifest."),
            handler=_write_manifest,
            depends_on=["export_reports"],
            produces=["manifest_path"],
        ),
        "telegram_market_brief": AgentSkill(
            skill_id="telegram_market_brief",
            metadata=meta("73-telegram-market-brief", "Send Telegram-ready 4-part market brief."),
            handler=_telegram_market_brief,
            depends_on=["daily_briefing"],
            produces=["notification_status"],
        ),
    }


def run_agent_plan(*, context: AgentRuntimeContext, registry: dict[str, AgentSkill], plan_steps: list[str]) -> DictStrAny:
    executed: list[DictStrAny] = []
    for step in plan_steps:
        skill = registry.get(step)
        if skill is None:
            result = AgentStepResult(skill_id=step, status="missing", summary="Skill not found in registry.")
            context.add_step_result(result)
            executed.append({"skill_id": step, "status": "missing", "summary": result.summary})
            continue
        payload = skill.handler(context)
        summary = str(payload.get("summary") or payload.get("headline") or skill.metadata.description).strip()
        status = str(payload.get("status") or "completed").strip().lower()
        context.add_step_result(AgentStepResult(skill_id=step, status=status, summary=summary, payload=dict(payload)))
        executed.append({"skill_id": step, "status": status, "summary": summary})

    final_summary = _build_final_agent_summary(context)
    return {
        "objective": context.objective,
        "plan_steps": plan_steps,
        "executed": executed,
        "final_summary": final_summary,
        "artifacts_output_dir": context.get_data("bundle_output_dir"),
        "manifest_path": context.get_data("manifest_path"),
    }


def _env_setup(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.load_dotenv_if_present()
    runtime_bundle = daily_run.load_runtime_config(context.config_dir)
    run_context = daily_run.build_run_context(runtime_bundle)
    context.runtime_bundle = runtime_bundle
    context.run_context = run_context
    context.set_data("runtime_bundle", runtime_bundle)
    context.set_data("run_context", run_context)
    return {
        "status": "ready",
        "summary": f"Initialized runtime for selection_mode={run_context.selection_mode}, run_id={run_context.run_id}.",
        "run_id": run_context.run_id,
    }


def _source_health(context: AgentRuntimeContext) -> DictStrAny:
    runtime_bundle = context.runtime_bundle
    payload = check_source_health(
        project_root=context.project_root,
        runtime_config=runtime_bundle.runtime,
        sources_config=runtime_bundle.sources,
    )
    context.set_data("source_health", payload)
    return payload


def _market_overview(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.load_market_overview_if_enabled(context.runtime_bundle, context.run_context)
    payload = dict(context.run_context.market_overview or {})
    context.set_data("market_overview", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("regime", {}).get("explanation", "Market overview unavailable.")).strip(),
        "payload": payload,
    }


def _ranking_selection(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.rank_candidates(context.runtime_bundle, context.run_context)
    daily_run.select_top_symbols(context.runtime_bundle, context.run_context)
    context.set_data("ranking_table", context.run_context.ranking_table.copy())
    context.set_data("selected_symbols", list(context.run_context.symbols_selected))
    return {
        "status": "ready" if context.run_context.symbols_selected else "missing",
        "summary": f"Selected {len(context.run_context.symbols_selected)} symbols: {', '.join(context.run_context.symbols_selected[:5])}.",
    }


def _deep_dive(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.build_deep_dive_for_symbols(context.runtime_bundle, context.run_context)
    payload = dict(context.run_context.deep_dive_payloads)
    context.set_data("deep_dives", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": f"Deep dives built for {len(payload)} symbols.",
    }


def _trade_plan(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.build_trade_plans(context.runtime_bundle, context.run_context)
    payload = dict(context.run_context.trade_plan_payloads)
    context.set_data("trade_plans", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": f"Trade plans built for {len(payload)} symbols.",
    }


def _daily_briefing(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    daily_run.compose_daily_briefing(context.runtime_bundle, context.run_context)
    payload = dict(context.run_context.daily_briefing_payload)
    context.set_data("daily_briefing", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("headline") or "Daily briefing created.").strip(),
    }


def _extract_vnindex_context(context: AgentRuntimeContext) -> DictStrAny:
    payload = dict(context.run_context.daily_briefing_payload.get("vnindex_context", {}))
    context.set_data("vnindex_context", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("headline") or "VNINDEX context unavailable.").strip(),
    }


def _extract_news_impact(context: AgentRuntimeContext) -> DictStrAny:
    payload = dict(context.run_context.daily_briefing_payload.get("news_impact", {}))
    context.set_data("news_impact", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("headline") or "News impact unavailable.").strip(),
    }


def _extract_long_candidates(context: AgentRuntimeContext) -> DictStrAny:
    payload = dict(context.run_context.daily_briefing_payload.get("long_candidates", {}))
    context.set_data("long_candidates", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("headline") or "Long candidate layer unavailable.").strip(),
    }


def _extract_entry_execution(context: AgentRuntimeContext) -> DictStrAny:
    payload = dict(context.run_context.daily_briefing_payload.get("entry_execution", {}))
    context.set_data("entry_execution", payload)
    return {
        "status": "ready" if payload else "missing",
        "summary": str(payload.get("portfolio_posture") or "Entry execution layer unavailable.").strip(),
    }


def _quality_gates(context: AgentRuntimeContext) -> DictStrAny:
    payload = run_quality_gates(
        market_overview=context.run_context.market_overview or {},
        top_opportunities=context.run_context.daily_briefing_payload.get("top_opportunities", []),
        trade_plan_payloads=context.run_context.trade_plan_payloads,
        daily_briefing=context.run_context.daily_briefing_payload,
        warnings=context.run_context.job_warnings,
    )
    context.set_data("quality_gates", payload)
    return payload


def _export_reports(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    if not context.export_reports:
        return {"status": "skipped", "summary": "Export disabled for current run."}
    daily_run.export_reports(context.runtime_bundle, context.run_context)
    context.set_data("bundle_output_dir", context.run_context.bundle_output_dir)
    return {
        "status": "ready",
        "summary": f"Reports exported to {context.run_context.bundle_output_dir}.",
    }


def _write_manifest(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    if not context.export_reports:
        return {"status": "skipped", "summary": "Manifest skipped because export is disabled."}
    daily_run.write_manifest(context.runtime_bundle, context.run_context)
    context.set_data("manifest_path", context.run_context.bundle_manifest_path)
    return {
        "status": "ready",
        "summary": f"Manifest written to {context.run_context.bundle_manifest_path}.",
    }


def _telegram_market_brief(context: AgentRuntimeContext) -> DictStrAny:
    import daily_run

    if not context.send_telegram:
        return {"status": "skipped", "summary": "Telegram sending disabled for current run."}
    daily_run.send_notification(context.runtime_bundle, context.run_context)
    payload = daily_run.build_final_summary(context.runtime_bundle, context.run_context)
    context.set_data("notification_status", payload)
    return {
        "status": "ready",
        "summary": "Telegram 4-part market brief sent.",
    }


def _build_final_agent_summary(context: AgentRuntimeContext) -> str:
    successes = sum(1 for result in context.step_results if result.status in {"ready", "completed"})
    total = len(context.step_results)
    headline = str(context.run_context.daily_briefing_payload.get("headline", "")).strip() if context.run_context else ""
    if headline:
        return f"Agent runtime completed {successes}/{total} steps. Headline: {headline}"
    return f"Agent runtime completed {successes}/{total} steps."


def build_agent_execution_package(
    *,
    project_root: Path,
    objective: str,
    config_dir: Path,
    ai_mode: str = "off",
    send_telegram: bool = False,
    export_reports: bool = True,
) -> DictStrAny:
    context = AgentRuntimeContext(
        project_root=project_root,
        objective=objective,
        config_dir=config_dir,
        ai_mode=ai_mode,
        send_telegram=send_telegram,
        export_reports=export_reports,
    )
    plan = build_agent_plan(objective=objective, send_telegram=send_telegram, export_reports=export_reports)
    registry = build_skill_registry(project_root=project_root)
    execution = run_agent_plan(context=context, registry=registry, plan_steps=list(plan.get("steps") or []))
    return {
        "planner": plan,
        "execution": execution,
    }


def save_agent_runtime_artifact(*, project_root: Path, run_id: str, payload: DictStrAny) -> str:
    target_dir = project_root / "artifacts" / run_id
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "agent_skill_runtime.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
