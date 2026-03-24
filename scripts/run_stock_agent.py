from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import daily_run
from services.quality_gates_service import run_quality_gates
from services.source_health_service import check_source_health


DictStrAny = dict[str, Any]
MARKET_NEWS_SUMMARY_PATH = PROJECT_ROOT / "data" / "derived" / "market_news_summary.json"
VALID_STOCK_SYMBOL_PATTERN = daily_run.VALID_STOCK_SYMBOL_PATTERN


@dataclass(slots=True)
class FlowStepResult:
    step_no: int
    name: str
    status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Official stock-agent runner with staged flow: ingestion, intelligence, action, operations, or all.",
    )
    parser.add_argument(
        "--stage",
        choices=["all", "ingestion", "intelligence", "action", "operations"],
        default="all",
        help="Run only one layer or the full stock-agent flow.",
    )
    parser.add_argument(
        "--config-dir",
        default=str(PROJECT_ROOT / "config"),
        help="Config directory.",
    )
    parser.add_argument(
        "--ai-mode",
        choices=["api", "file", "off"],
        default="api",
        help="AI overlay mode.",
    )
    parser.add_argument("--openai-model", default=None)
    parser.add_argument("--openai-base-url", default=None)
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument("--response-file", default=None)
    parser.add_argument("--skip-scan", action="store_true")
    parser.add_argument("--skip-overview", action="store_true")
    return parser.parse_args()


def _set_ai_env(args: argparse.Namespace) -> None:
    if args.ai_mode == "off":
        daily_run.os.environ["AI_ANALYSIS_ENABLED"] = "false"
        return

    daily_run.os.environ["AI_ANALYSIS_ENABLED"] = "true"
    daily_run.os.environ["AI_ANALYSIS_MODE"] = args.ai_mode
    if args.openai_model:
        daily_run.os.environ["OPENAI_MODEL"] = str(args.openai_model).strip()
    if args.openai_base_url:
        daily_run.os.environ["OPENAI_BASE_URL"] = str(args.openai_base_url).strip()
    if args.ai_mode == "file":
        prompt_file = args.prompt_file or str(PROJECT_ROOT / "artifacts" / "ai_prompt.json")
        response_file = args.response_file or str(PROJECT_ROOT / "artifacts" / "ai_response.json")
        daily_run.os.environ["AI_ANALYSIS_PROMPT_FILE"] = prompt_file
        daily_run.os.environ["AI_ANALYSIS_RESPONSE_FILE"] = response_file


def _flow_output_dir(run_id: str) -> Path:
    target = PROJECT_ROOT / "artifacts" / run_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def _record_step(results: list[FlowStepResult], step_no: int, name: str, fn: Callable[[], str]) -> None:
    try:
        detail = fn()
        results.append(FlowStepResult(step_no=step_no, name=name, status="completed", detail=detail))
    except Exception as exc:
        results.append(
            FlowStepResult(
                step_no=step_no,
                name=name,
                status="failed",
                detail=f"{type(exc).__name__}: {exc}",
            )
        )
        raise


def _run_subset(stage: str, args: argparse.Namespace) -> tuple[daily_run.RuntimeConfigBundle, daily_run.RunContext, list[FlowStepResult]]:
    config_dir = Path(args.config_dir).resolve()
    runtime_bundle = daily_run.load_runtime_config(config_dir)
    context = daily_run.build_run_context(runtime_bundle)
    results: list[FlowStepResult] = []

    runtime, sources = runtime_bundle.runtime, runtime_bundle.sources
    source_health = check_source_health(
        project_root=PROJECT_ROOT,
        runtime_config=runtime,
        sources_config=sources,
    )

    _record_step(results, 1, "load_runtime_config_and_mode", lambda: f"mode={context.mode}, selection_mode={context.selection_mode}")
    _record_step(results, 2, "initialize_run_context_and_manifest_skeleton", lambda: f"run_id={context.run_id}")
    _record_step(results, 3, "check_source_health_and_fallback", lambda: json.dumps(source_health, ensure_ascii=False))

    if stage in {"all", "ingestion"}:
        _record_step(
            results,
            4,
            "run_market_wide_and_universe_skills",
            lambda: _run_ingestion_steps(runtime_bundle, context, args),
        )
        if stage == "ingestion":
            return runtime_bundle, context, results

    if stage in {"all", "intelligence"}:
        _record_step(
            results,
            5,
            "normalize_merge_and_validate_skill_outputs",
            lambda: _run_normalization_step(runtime_bundle, context),
        )
        if not args.skip_overview:
            _record_step(
                results,
                6,
                "build_market_overview_foundation",
                lambda: _run_market_overview_step(runtime_bundle, context),
            )
        _record_step(results, 7, "build_symbol_profiles", lambda: _run_profile_steps(runtime_bundle, context))
        _record_step(results, 8, "rank_and_select_top_candidates", lambda: _run_ranking_steps(runtime_bundle, context))
        _record_step(results, 9, "aggregate_market_and_symbol_news", lambda: _news_context_step(context))
        _record_step(results, 10, "deep_dive_top_10", lambda: _run_deep_dive_steps(runtime_bundle, context))
        _record_step(results, 11, "openai_market_and_symbol_synthesis", lambda: _run_briefing_steps(runtime_bundle, context, with_ai=True))
        if stage == "intelligence":
            return runtime_bundle, context, results

    if stage in {"all", "action"}:
        _ensure_action_inputs(runtime_bundle, context, with_ai=True)
        _record_step(results, 12, "generate_trade_plans", lambda: _run_trade_plan_step(runtime_bundle, context))
        _record_step(results, 13, "apply_risk_and_portfolio_constraints", lambda: _risk_portfolio_step(context))
        _record_step(results, 14, "run_quality_gates", lambda: _quality_gate_step(context))
        if stage == "action":
            return runtime_bundle, context, results

    if stage in {"all", "operations"}:
        _ensure_operations_inputs(runtime_bundle, context, with_ai=True)
        _record_step(results, 15, "export_reports", lambda: _export_step(runtime_bundle, context))
        _record_step(results, 16, "write_manifest_and_metrics", lambda: _manifest_metrics_step(runtime_bundle, context))
        _record_step(results, 17, "send_notification", lambda: _notification_step(runtime_bundle, context))
        _record_step(results, 18, "upload_artifact_and_store_run_history", lambda: _artifact_history_step(context))
        _record_step(results, 19, "scheduler_ready_for_next_run", lambda: "Workflow ready for cron/workflow_dispatch rerun.")

    return runtime_bundle, context, results


def _run_ingestion_steps(
    runtime_bundle: daily_run.RuntimeConfigBundle,
    context: daily_run.RunContext,
    args: argparse.Namespace,
) -> str:
    messages: list[str] = []
    if args.skip_scan:
        messages.append("scan skipped")
    else:
        daily_run.scan_universe(runtime_bundle, context)
        messages.append(f"scan completed total_scanned={context.total_scanned}")

    if args.skip_overview:
        messages.append("overview skipped")
    else:
        daily_run.load_market_overview_if_enabled(runtime_bundle, context)
        messages.append(f"overview_loaded={bool(context.market_overview)}")

    return ", ".join(messages)


def _run_market_overview_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    daily_run.load_market_overview_if_enabled(runtime_bundle, context)
    return f"market_overview_loaded={bool(context.market_overview)}"


def _run_normalization_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    if context.ranking_table.empty:
        daily_run.rank_candidates(runtime_bundle, context)
    if not context.symbols_selected:
        daily_run.select_top_symbols(runtime_bundle, context)

    raw_scan_df = _load_csv_if_exists(daily_run.RAW_SCAN_OUTPUT_PATH)
    ranking_df = context.ranking_table.copy()
    selected_symbols = _normalize_symbol_list(context.symbols_selected)
    data_quality_warnings: list[str] = []

    if ranking_df.empty:
        data_quality_warnings.append("ranking_table_missing")
    else:
        ranking_df = _normalize_runtime_dataframe(ranking_df)
        context.ranking_table = ranking_df

    if not raw_scan_df.empty:
        raw_scan_df = _normalize_runtime_dataframe(raw_scan_df)

    matched_rows = 0
    if not raw_scan_df.empty and selected_symbols:
        matched_rows = int(raw_scan_df["symbol"].astype(str).str.upper().isin(selected_symbols).sum())
        if matched_rows < len(selected_symbols):
            data_quality_warnings.append("selected_symbols_missing_in_raw_scan")

    normalized_runtime = {
        "status": "ready" if not data_quality_warnings else "degraded",
        "raw_market_rows": int(len(raw_scan_df)),
        "ranking_rows": int(len(ranking_df)),
        "selected_symbol_count": len(selected_symbols),
        "selected_symbols": selected_symbols,
        "selected_symbols_in_raw_scan": matched_rows,
        "warnings": data_quality_warnings,
        "score_column_ready": bool(not ranking_df.empty and "score" in ranking_df.columns),
    }
    _attach_runtime_payload(context, "normalized_runtime", normalized_runtime)
    return json.dumps(normalized_runtime, ensure_ascii=False)


def _run_ranking_steps(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    daily_run.rank_candidates(runtime_bundle, context)
    daily_run.select_top_symbols(runtime_bundle, context)
    return f"ranked={context.total_ranked}, selected={context.total_selected}"


def _run_profile_steps(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    if context.total_selected == 0:
        daily_run.rank_candidates(runtime_bundle, context)
        daily_run.select_top_symbols(runtime_bundle, context)
    return f"symbol_profile_candidates={len(context.symbols_selected)} source={context.selection_source}"


def _news_context_step(context: daily_run.RunContext) -> str:
    selected_symbols = _normalize_symbol_list(context.symbols_selected)
    raw_scan_df = _normalize_runtime_dataframe(_load_csv_if_exists(daily_run.RAW_SCAN_OUTPUT_PATH))
    market_summary = _load_json_if_exists(MARKET_NEWS_SUMMARY_PATH)

    symbol_summaries: dict[str, dict[str, Any]] = {}
    if not raw_scan_df.empty and selected_symbols:
        working_df = raw_scan_df[raw_scan_df["symbol"].astype(str).str.upper().isin(selected_symbols)].copy()
        for _, row in working_df.iterrows():
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            symbol_summaries[symbol] = {
                "symbol": symbol,
                "news_count": _to_int(row.get("news_count")),
                "news_signal": _to_float(row.get("news_signal")),
                "sentiment_summary": str(row.get("sentiment_summary", "No material news detected.")).strip(),
                "catalyst_tags": _split_csv_tags(row.get("catalyst_tags")),
                "risk_tags": _split_csv_tags(row.get("risk_tags")),
                "themes": _split_csv_tags(row.get("themes")),
                "headline_digest": [],
            }

    news_context = {
        "status": "ready" if market_summary or symbol_summaries else "degraded",
        "market_summary": market_summary,
        "symbol_summaries": symbol_summaries,
        "selected_symbol_count": len(selected_symbols),
        "symbols_with_news_context": len(symbol_summaries),
        "news_items_total": int(sum(item.get("news_count", 0) for item in symbol_summaries.values())),
    }
    _attach_runtime_payload(context, "news_context", news_context)
    return json.dumps(
        {
            "status": news_context["status"],
            "symbols_with_news_context": news_context["symbols_with_news_context"],
            "market_summary_ready": bool(market_summary),
            "news_items_total": news_context["news_items_total"],
        },
        ensure_ascii=False,
    )


def _run_deep_dive_steps(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    if not context.symbols_selected:
        daily_run.rank_candidates(runtime_bundle, context)
        daily_run.select_top_symbols(runtime_bundle, context)
    daily_run.build_deep_dive_for_symbols(runtime_bundle, context)
    return f"deep_dives_built={context.deep_dives_built}"


def _run_briefing_steps(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext, *, with_ai: bool) -> str:
    if not context.trade_plan_payloads and context.symbol_results:
        daily_run.build_trade_plans(runtime_bundle, context)
    preserved_runtime_payloads = _extract_runtime_payloads(context)
    daily_run.compose_daily_briefing(runtime_bundle, context)
    _restore_runtime_payloads(context, preserved_runtime_payloads)
    if with_ai:
        daily_run.compose_ai_briefing(runtime_bundle, context)
    return f"headline={context.daily_briefing_payload.get('headline')}"


def _run_trade_plan_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    if not context.symbols_selected:
        daily_run.rank_candidates(runtime_bundle, context)
        daily_run.select_top_symbols(runtime_bundle, context)
    if not context.symbol_results:
        daily_run.build_deep_dive_for_symbols(runtime_bundle, context)
    daily_run.build_trade_plans(runtime_bundle, context)
    if not _has_composed_briefing(context):
        preserved_runtime_payloads = _extract_runtime_payloads(context)
        daily_run.compose_daily_briefing(runtime_bundle, context)
        _restore_runtime_payloads(context, preserved_runtime_payloads)
        daily_run.compose_ai_briefing(runtime_bundle, context)
    return f"trade_plans_built={context.trade_plans_built}"


def _risk_portfolio_step(context: daily_run.RunContext) -> str:
    skill_pipeline = context.daily_briefing_payload.get("skill_pipeline", {})
    if not isinstance(skill_pipeline, dict):
        return "skill_pipeline missing"
    stages = skill_pipeline.get("stages", {})
    if not isinstance(stages, dict):
        return "risk/portfolio stage data missing"
    risk_summary = stages.get("risk_engine", {}).get("summary")
    portfolio_summary = stages.get("portfolio_auditor", {}).get("summary")
    return f"risk={risk_summary}; portfolio={portfolio_summary}"


def _quality_gate_step(context: daily_run.RunContext) -> str:
    quality = run_quality_gates(
        market_overview=context.market_overview or {},
        top_opportunities=context.daily_briefing_payload.get("top_opportunities", []),
        trade_plan_payloads=context.trade_plan_payloads,
        daily_briefing=context.daily_briefing_payload,
        warnings=context.job_warnings,
    )
    context.daily_briefing_payload["quality_gates"] = quality
    return json.dumps(quality, ensure_ascii=False)


def _export_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    if not _has_composed_briefing(context):
        preserved_runtime_payloads = _extract_runtime_payloads(context)
        daily_run.compose_daily_briefing(runtime_bundle, context)
        _restore_runtime_payloads(context, preserved_runtime_payloads)
        daily_run.compose_ai_briefing(runtime_bundle, context)
    daily_run.export_reports(runtime_bundle, context)
    return f"output_dir={context.bundle_output_dir}"


def _manifest_metrics_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    daily_run.write_manifest(runtime_bundle, context)
    summary = daily_run.build_final_summary(runtime_bundle, context)
    return f"manifest_path={summary.get('manifest_path')}"


def _notification_step(runtime_bundle: daily_run.RuntimeConfigBundle, context: daily_run.RunContext) -> str:
    daily_run.send_notification(runtime_bundle, context)
    return "notification step completed"


def _artifact_history_step(context: daily_run.RunContext) -> str:
    output_dir = _flow_output_dir(context.run_id)
    flow_path = output_dir / "stock_agent_flow.json"
    history_payload = {
        "run_id": context.run_id,
        "generated_at": datetime.now().isoformat(),
        "artifacts_output_dir": context.bundle_output_dir,
        "manifest_path": context.bundle_manifest_path,
        "files_created": context.files_created,
    }
    flow_path.write_text(json.dumps(history_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"history_saved={flow_path}"


def _ensure_intelligence_inputs(
    runtime_bundle: daily_run.RuntimeConfigBundle,
    context: daily_run.RunContext,
    *,
    with_ai: bool,
) -> None:
    if context.ranking_table.empty or not context.symbols_selected:
        _run_normalization_step(runtime_bundle, context)
    if not context.market_overview:
        daily_run.load_market_overview_if_enabled(runtime_bundle, context)
    if not context.symbols_selected:
        daily_run.rank_candidates(runtime_bundle, context)
        daily_run.select_top_symbols(runtime_bundle, context)
    _news_context_step(context)
    if not context.symbol_results:
        daily_run.build_deep_dive_for_symbols(runtime_bundle, context)
    if not context.trade_plan_payloads:
        daily_run.build_trade_plans(runtime_bundle, context)
    if not _has_composed_briefing(context):
        _run_briefing_steps(runtime_bundle, context, with_ai=with_ai)


def _ensure_action_inputs(
    runtime_bundle: daily_run.RuntimeConfigBundle,
    context: daily_run.RunContext,
    *,
    with_ai: bool,
) -> None:
    _ensure_intelligence_inputs(runtime_bundle, context, with_ai=with_ai)


def _ensure_operations_inputs(
    runtime_bundle: daily_run.RuntimeConfigBundle,
    context: daily_run.RunContext,
    *,
    with_ai: bool,
) -> None:
    _ensure_action_inputs(runtime_bundle, context, with_ai=with_ai)
    if "quality_gates" not in context.daily_briefing_payload:
        _quality_gate_step(context)


def _attach_runtime_payload(context: daily_run.RunContext, key: str, payload: dict[str, Any]) -> None:
    if not isinstance(context.daily_briefing_payload, dict):
        context.daily_briefing_payload = {}
    context.daily_briefing_payload[key] = dict(payload)


def _extract_runtime_payloads(context: daily_run.RunContext) -> dict[str, dict[str, Any]]:
    payload = context.daily_briefing_payload if isinstance(context.daily_briefing_payload, dict) else {}
    extras: dict[str, dict[str, Any]] = {}
    for key in ("normalized_runtime", "news_context"):
        value = payload.get(key)
        if isinstance(value, dict):
            extras[key] = dict(value)
    return extras


def _restore_runtime_payloads(context: daily_run.RunContext, extras: dict[str, dict[str, Any]]) -> None:
    for key, value in extras.items():
        _attach_runtime_payload(context, key, value)


def _has_composed_briefing(context: daily_run.RunContext) -> bool:
    payload = context.daily_briefing_payload if isinstance(context.daily_briefing_payload, dict) else {}
    return bool(payload.get("headline")) or bool(payload.get("top_opportunities"))


def _load_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _normalize_runtime_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    working_df.columns = [str(column).strip().lower() for column in working_df.columns]
    if "symbol" in working_df.columns:
        working_df["symbol"] = working_df["symbol"].astype(str).str.strip().str.upper()
        working_df = working_df[working_df["symbol"].str.match(VALID_STOCK_SYMBOL_PATTERN, na=False)]
        working_df = working_df.drop_duplicates(subset=["symbol"]).reset_index(drop=True)
    if "score" not in working_df.columns:
        if "final_score" in working_df.columns:
            working_df["score"] = pd.to_numeric(working_df["final_score"], errors="coerce")
        elif "raw_score" in working_df.columns:
            working_df["score"] = pd.to_numeric(working_df["raw_score"], errors="coerce")
    return working_df


def _normalize_symbol_list(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    for symbol in symbols:
        candidate = str(symbol).strip().upper()
        if candidate and VALID_STOCK_SYMBOL_PATTERN.match(candidate) and candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _split_csv_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _serialize_steps(results: list[FlowStepResult]) -> list[dict[str, Any]]:
    return [
        {
            "step_no": item.step_no,
            "name": item.name,
            "status": item.status,
            "detail": item.detail,
        }
        for item in results
    ]


def _save_flow_trace(context: daily_run.RunContext, results: list[FlowStepResult]) -> Path:
    output_dir = _flow_output_dir(context.run_id)
    path = output_dir / "flow_trace.json"
    payload = {
        "run_id": context.run_id,
        "generated_at": datetime.now().isoformat(),
        "steps": _serialize_steps(results),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    daily_run.configure_logging()
    daily_run.load_dotenv_if_present()
    _set_ai_env(args)

    runtime_bundle, context, results = _run_subset(args.stage, args)
    summary = daily_run.build_final_summary(runtime_bundle, context)
    flow_trace_path = _save_flow_trace(context, results)

    print("STOCK AGENT RUN")
    print(f"- stage={args.stage}")
    print(f"- run_id={summary.get('run_id')}")
    print(f"- headline={summary.get('headline')}")
    print(f"- terminal_mode={summary.get('terminal_mode')}")
    print(f"- output_dir={summary.get('artifacts_output_dir')}")
    print(f"- manifest_path={summary.get('manifest_path')}")
    print(f"- flow_trace={flow_trace_path}")
    for item in results:
        print(f"- step_{item.step_no}_{item.name}={item.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
