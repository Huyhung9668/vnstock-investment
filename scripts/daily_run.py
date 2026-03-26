from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notifiers.telegram import TelegramNotifier, build_daily_summary_message, build_daily_summary_messages
from providers.factory import create_provider
from services.ai_analysis_service import (
    ai_analysis_ready,
    build_ai_daily_briefing,
    load_ai_analysis_config,
)
from services.analysis_builder import build_analysis_package
from services.chief_analysis_writer_service import build_chief_analysis
from services.daily_briefing_service import build_daily_briefing
from services.market_overview_service import build_market_overview
from services.terminal_orchestrator_service import build_terminal_orchestration
from services.manifest_service import create_manifest, save_manifest
from services.report_export_service import export_report_bundle
from services.report_exporter import export_markdown_report
from services.trade_plan_service import generate_trade_plan, render_trade_plan


DictStrAny = dict[str, Any]
CONFIG_DIR = PROJECT_ROOT / "config"
TOP_SYMBOLS_PATH = PROJECT_ROOT / "data" / "derived" / "top10_symbols.json"
MARKET_OVERVIEW_PATH = PROJECT_ROOT / "data" / "derived" / "market_overview.json"
RANKING_TABLE_PATH = PROJECT_ROOT / "data" / "derived" / "universe_scores.csv"
RAW_SCAN_OUTPUT_PATH = PROJECT_ROOT / "data" / "derived" / "universe_scan_raw.csv"
DOTENV_PATH = PROJECT_ROOT / ".env"
VALID_STOCK_SYMBOL_PATTERN = re.compile(r"^[A-Z]{3,4}$")
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
)


@dataclass(slots=True)
class RuntimeConfigBundle:
    config_dir: Path
    runtime: DictStrAny
    sources: DictStrAny
    watchlist: DictStrAny
    universe: DictStrAny


@dataclass(slots=True)
class RunContext:
    run_id: str
    started_at: float
    mode: str
    selection_mode: str
    report_dir: Path
    manifest_dir: Path
    primary_provider: str
    fallback_provider: str | None
    job_warnings: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    market_overview: DictStrAny | None = None
    market_overview_path: str | None = None
    ranking_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    ranking_source: str | None = None
    ranking_fallback_used: bool = False
    symbols_selected: list[str] = field(default_factory=list)
    selection_source: str | None = None
    selection_fallback_used: bool = False
    symbol_results: list["SymbolRunResult"] = field(default_factory=list)
    trade_plan_payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    deep_dive_payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    daily_briefing_payload: dict[str, Any] = field(default_factory=dict)
    ai_analysis_payload: dict[str, Any] = field(default_factory=dict)
    bundle_output_dir: str | None = None
    bundle_manifest_path: str | None = None
    total_scanned: int = 0
    total_ranked: int = 0
    total_selected: int = 0
    deep_dives_built: int = 0
    trade_plans_built: int = 0


@dataclass(slots=True)
class SymbolRunResult:
    symbol: str
    status: str
    source_used: str
    fallback_used: bool
    degraded_mode: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    report_path: str | None = None
    analysis_data: DictStrAny = field(default_factory=dict)
    trade_plan_data: DictStrAny = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily investment pipeline.")
    parser.add_argument(
        "--config-dir",
        default=str(CONFIG_DIR),
        help="Directory containing runtime.yaml, sources.yaml, watchlist.yaml and optional universe.yaml.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def load_dotenv_if_present(path: Path = DOTENV_PATH) -> None:
    if not path.exists():
        clear_runtime_proxies()
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key or normalized_key in os.environ:
            continue

        normalized_value = value.strip().strip('"').strip("'")
        os.environ[normalized_key] = normalized_value

    clear_runtime_proxies()


def clear_runtime_proxies() -> None:
    for key in PROXY_ENV_KEYS:
        if key in os.environ:
            os.environ.pop(key, None)


def _log_step_start(name: str) -> None:
    logging.info("STEP START | %s", name)


def _log_step_end(name: str) -> None:
    logging.info("STEP END | %s", name)


def _log_step_end_with_counts(name: str, **counts: int) -> None:
    filtered_counts = {key: value for key, value in counts.items() if value is not None}
    if filtered_counts:
        details = " | ".join(f"{key}={value}" for key, value in filtered_counts.items())
        logging.info("STEP END | %s | %s", name, details)
    else:
        logging.info("STEP END | %s", name)


def _warn(context: RunContext, message: str) -> None:
    context.job_warnings.append(message)
    logging.warning(message)


def _warn_step(context: RunContext, step_name: str, message: str) -> None:
    _warn(context, f"step={step_name} | {message}")


def _warn_symbol(context: RunContext, symbol: str, message: str) -> None:
    _warn(context, f"symbol={symbol} | {message}")


def _re_raise_if_keyboard_interrupt(exc: BaseException) -> None:
    if isinstance(exc, KeyboardInterrupt):
        raise exc


def _log_error(step_name: str, exc: Exception, *, symbol: str | None = None) -> None:
    prefix = f"step={step_name}"
    if symbol:
        prefix += f" | symbol={symbol}"
    logging.error("%s | %s: %s", prefix, type(exc).__name__, exc)


def _load_yaml(path: Path, *, default: DictStrAny | None = None) -> DictStrAny:
    if not path.exists():
        if default is not None:
            return dict(default)
        raise FileNotFoundError(f"Missing config file: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def _env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _apply_env_overrides(runtime_config: DictStrAny, sources_config: DictStrAny) -> tuple[DictStrAny, DictStrAny]:
    runtime = dict(runtime_config)
    sources = dict(sources_config)

    telegram_enabled = _env_bool("TELEGRAM_ENABLED")
    telegram_bot_token = _env_str("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _env_str("TELEGRAM_CHAT_ID")

    if any(value is not None for value in [telegram_enabled, telegram_bot_token, telegram_chat_id]):
        notification = runtime.get("notification")
        if not isinstance(notification, dict):
            notification = {}
        else:
            notification = dict(notification)

        telegram = notification.get("telegram")
        if not isinstance(telegram, dict):
            telegram = {}
        else:
            telegram = dict(telegram)

        if telegram_enabled is not None:
            telegram["enabled"] = telegram_enabled
        if telegram_bot_token is not None:
            telegram["bot_token"] = telegram_bot_token
        if telegram_chat_id is not None:
            telegram["chat_id"] = telegram_chat_id

        notification["telegram"] = telegram
        runtime["notification"] = notification

    market_provider = _env_str("MARKET_PROVIDER")
    news_provider = _env_str("NEWS_PROVIDER")
    financials_provider = _env_str("FINANCIALS_PROVIDER")

    if any(value is not None for value in [market_provider, news_provider, financials_provider]):
        services = sources.get("services")
        if not isinstance(services, dict):
            services = {}
        else:
            services = dict(services)

        if market_provider is not None:
            services["market"] = market_provider.lower()
        if news_provider is not None:
            services["news"] = news_provider.lower()
        if financials_provider is not None:
            services["financials"] = financials_provider.lower()

        sources["services"] = services

    return runtime, sources


def _normalize_symbol(value: Any) -> str:
    return str(value).strip().upper()


def _is_valid_stock_symbol(symbol: str) -> bool:
    return bool(VALID_STOCK_SYMBOL_PATTERN.fullmatch(symbol.strip().upper()))


def _load_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _normalize_ranking_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    working_df = df.copy()
    working_df.columns = [str(column).strip() for column in working_df.columns]
    if "symbol" not in working_df.columns:
        return pd.DataFrame()

    working_df["symbol"] = working_df["symbol"].astype(str).str.strip().str.upper()
    working_df = working_df[working_df["symbol"].apply(_is_valid_stock_symbol)].reset_index(drop=True)
    working_df = working_df[working_df["symbol"] != ""].drop_duplicates(subset=["symbol"]).reset_index(drop=True)

    if "score" not in working_df.columns:
        if "final_score" in working_df.columns:
            working_df["score"] = working_df["final_score"]
        elif "raw_score" in working_df.columns:
            working_df["score"] = working_df["raw_score"]

    if "score" in working_df.columns:
        working_df["score"] = pd.to_numeric(working_df["score"], errors="coerce")
        working_df = working_df.sort_values(
            by=["score", "symbol"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)

    working_df["rank"] = range(1, len(working_df) + 1)
    return working_df


def _load_watchlist_symbols(watchlist_config: DictStrAny) -> list[str]:
    raw_symbols = watchlist_config.get("symbols")
    if not isinstance(raw_symbols, list):
        return []
    return [
        _normalize_symbol(item)
        for item in raw_symbols
        if _normalize_symbol(item) and _is_valid_stock_symbol(_normalize_symbol(item))
    ]


def _resolve_top_symbols_path(runtime_config: DictStrAny) -> Path:
    selection = runtime_config.get("selection", {})
    configured_path = selection.get("universe_top_file")
    if isinstance(configured_path, str) and configured_path.strip():
        return PROJECT_ROOT / configured_path.strip()
    return TOP_SYMBOLS_PATH


def _load_json_symbol_list(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list[str] at {path}")
    return [
        _normalize_symbol(item)
        for item in payload
        if _normalize_symbol(item) and _is_valid_stock_symbol(_normalize_symbol(item))
    ]


def _selection_mode(runtime_config: DictStrAny) -> str:
    selection = runtime_config.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("config/runtime.yaml: selection must be a mapping")
    mode = selection.get("mode")
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("config/runtime.yaml: selection.mode must be a non-empty string")
    return mode.strip().lower()


def _mode(runtime_config: DictStrAny) -> str:
    mode = runtime_config.get("mode")
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("config/runtime.yaml: mode must be a non-empty string")
    return mode.strip().lower()


def _output_dirs(runtime_config: DictStrAny) -> tuple[Path, Path]:
    output = runtime_config.get("output")
    if not isinstance(output, dict):
        raise ValueError("config/runtime.yaml: output must be a mapping")

    report_dir = output.get("report_dir")
    manifest_dir = output.get("manifest_dir")
    if not isinstance(report_dir, str) or not report_dir.strip():
        raise ValueError("config/runtime.yaml: output.report_dir must be a non-empty string")
    if not isinstance(manifest_dir, str) or not manifest_dir.strip():
        raise ValueError("config/runtime.yaml: output.manifest_dir must be a non-empty string")

    return PROJECT_ROOT / report_dir.strip(), PROJECT_ROOT / manifest_dir.strip()


def _provider_names(sources_config: DictStrAny) -> tuple[str, str | None]:
    providers = sources_config.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("config/sources.yaml: providers must be a mapping")

    primary = providers.get("primary")
    fallback = providers.get("fallback")
    if not isinstance(primary, str) or not primary.strip():
        raise ValueError("config/sources.yaml: providers.primary must be a non-empty string")

    normalized_fallback = None
    if isinstance(fallback, str) and fallback.strip():
        normalized_fallback = fallback.strip().lower()

    return primary.strip().lower(), normalized_fallback


def _market_overview_enabled(runtime_config: DictStrAny) -> bool:
    features = runtime_config.get("features")
    if not isinstance(features, dict):
        return False
    return bool(features.get("market_overview", False))


def _telegram_config(runtime_config: DictStrAny) -> dict[str, Any]:
    notification = runtime_config.get("notification")
    if not isinstance(notification, dict):
        return {}

    telegram = notification.get("telegram")
    if not isinstance(telegram, dict):
        return {}

    return dict(telegram)


def _telegram_enabled(runtime_config: DictStrAny) -> bool:
    telegram = _telegram_config(runtime_config)
    return bool(telegram.get("enabled", False))


def _section_status(data_quality: DictStrAny, section_name: str) -> str:
    sections = data_quality.get("sections")
    if not isinstance(sections, dict):
        return "unknown"
    section = sections.get(section_name)
    if not isinstance(section, dict):
        return "unknown"
    status = section.get("status")
    return str(status).strip().lower() if status is not None else "unknown"


def _build_analysis_warnings(analysis_package: Any) -> tuple[list[str], bool]:
    warnings: list[str] = []
    degraded_mode = False

    financial_status = _section_status(analysis_package.data_quality, "financial_summary")
    news_status = _section_status(analysis_package.data_quality, "news_summary")
    breadth_status = _section_status(analysis_package.data_quality, "breadth_context")

    if financial_status == "error":
        warnings.append("financial_summary error; continuing with degraded output")
    elif financial_status == "missing":
        warnings.append("financial_summary missing; continuing with reduced context")

    if news_status == "error":
        warnings.append("news_summary error; continuing with degraded output")
    elif news_status == "missing":
        warnings.append("news_summary missing; continuing with reduced context")

    if breadth_status == "error":
        warnings.append("breadth_context error; continuing with reduced context")
    elif breadth_status == "missing":
        warnings.append("breadth_context missing; continuing with reduced context")

    return warnings, degraded_mode


def _synthesize_market_overview_from_ranking(context: RunContext) -> None:
    if context.market_overview or context.ranking_table.empty:
        return

    try:
        market_overview = build_market_overview(context.ranking_table.copy())
    except Exception as exc:
        _log_error("synthesize_market_overview_from_ranking", exc)
        _warn_step(context, "synthesize_market_overview_from_ranking", f"failed: {type(exc).__name__}: {exc}")
        return

    if not isinstance(market_overview, dict) or not market_overview:
        return

    market_overview["summary"] = (
        "Market overview duoc tong hop tu ranking table de bo sung breadth context "
        "khi provider khong tra ve overview rieng."
    )
    market_overview["source"] = "ranking_table_fallback"
    context.market_overview = market_overview
    context.market_overview_path = "in_memory:ranking_table_fallback"
    logging.info("market_overview_path=%s", context.market_overview_path)


def _build_breadth_context_override(context: RunContext) -> dict[str, Any] | None:
    market_overview = context.market_overview
    if not isinstance(market_overview, dict) or not market_overview:
        return None

    breadth = market_overview.get("breadth")
    regime = market_overview.get("regime")
    index_context = market_overview.get("index_context")

    payload: DictStrAny = {}
    if isinstance(breadth, dict) and breadth:
        payload["breadth"] = dict(breadth)
    if isinstance(regime, dict) and regime:
        payload["regime"] = dict(regime)
    if isinstance(index_context, dict) and index_context:
        payload["index_context"] = dict(index_context)

    sector_rotation = market_overview.get("sector_rotation")
    if isinstance(sector_rotation, list) and sector_rotation:
        payload["sector_rotation"] = [dict(item) for item in sector_rotation if isinstance(item, dict)]

    liquidity_concentration = market_overview.get("liquidity_concentration")
    if isinstance(liquidity_concentration, dict) and liquidity_concentration:
        payload["liquidity_concentration"] = dict(liquidity_concentration)

    if not payload:
        return None

    payload["source"] = str(market_overview.get("source") or "market_overview")
    return payload


def _deep_dive_symbol_delay_seconds(runtime_config: DictStrAny) -> float:
    env_override = _env_str("DEEP_DIVE_SYMBOL_DELAY_SECONDS")
    if env_override is not None:
        try:
            return max(0.0, float(env_override))
        except ValueError:
            return 0.0

    provider_runtime = runtime_config.get("provider_runtime")
    if not isinstance(provider_runtime, dict):
        return 0.0

    request_delay = provider_runtime.get("request_delay_seconds", 0.0)
    try:
        request_delay_value = float(request_delay)
    except (TypeError, ValueError):
        request_delay_value = 0.0

    return max(0.0, request_delay_value)


def _build_degraded_trade_plan(symbol: str, reason: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "setup_type": "degraded",
        "thesis": "Trade plan degraded do loi tao ke hoach hoac thieu du lieu.",
        "entry_zone": {},
        "confirmation": [],
        "invalidation": "Can review thu cong truoc khi giao dich.",
        "target": {},
        "stop_loss": None,
        "risk_reward": None,
        "position_sizing_hint": "Khong mo vi the lon cho den khi co them du lieu xac nhan.",
        "monitoring_checklist": ["Kiem tra lai du lieu dau vao truoc khi giao dich."],
        "notes": [reason],
        "degraded_mode": True,
    }


def _render_degraded_trade_plan_markdown(symbol: str, trade_plan: dict[str, Any]) -> str:
    notes = trade_plan.get("notes", [])
    if not isinstance(notes, list) or not notes:
        notes = ["Khong co ghi chu bo sung."]
    return "\n".join(
        [
            f"# Trade Plan: {symbol}",
            "",
            "- Thesis: Trade plan degraded do loi tao ke hoach.",
            "- Setup type: degraded",
            "- Invalidation: Can review thu cong truoc khi giao dich.",
            "- Degraded mode: true",
            "",
            "## Notes",
            *[f"- {note}" for note in notes],
            "",
        ]
    )


def _build_ranking_from_raw_scan(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()

    working_df = df.copy()
    working_df.columns = [str(column).strip().lower() for column in working_df.columns]
    working_df["symbol"] = working_df["symbol"].astype(str).str.strip().str.upper()

    score_seed = pd.Series(0.0, index=working_df.index)
    if "return_3m" in working_df.columns:
        working_df["return_3m"] = pd.to_numeric(working_df["return_3m"], errors="coerce").fillna(0.0)
        score_seed = score_seed.add(working_df["return_3m"], fill_value=0.0)
    if "avg_volume" in working_df.columns:
        working_df["avg_volume"] = pd.to_numeric(working_df["avg_volume"], errors="coerce").fillna(0.0)
        score_seed = score_seed.add(working_df["avg_volume"].rank(method="dense", pct=True), fill_value=0.0)
    if "last_price" in working_df.columns:
        working_df["last_price"] = pd.to_numeric(working_df["last_price"], errors="coerce").fillna(0.0)

    working_df["score"] = score_seed
    return _normalize_ranking_dataframe(working_df)


def _serialize_symbol_results(symbol_results: list["SymbolRunResult"]) -> list[DictStrAny]:
    serialized: list[DictStrAny] = []
    for item in symbol_results:
        serialized.append(
            {
                "symbol": item.symbol,
                "status": item.status,
                "source_used": item.source_used,
                "fallback_used": item.fallback_used,
                "degraded_mode": item.degraded_mode,
                "warnings": list(item.warnings),
                "errors": list(item.errors),
                "report_path": item.report_path,
                "manifest_path": item.manifest_path,
            }
        )
    return serialized


def _build_symbol_artifacts(
    *,
    context: RunContext,
    symbol: str,
    provider_name: str,
    runtime_bundle: RuntimeConfigBundle,
) -> SymbolRunResult:
    provider = create_provider(name=provider_name, mode=context.mode, config=runtime_bundle.sources)
    analysis_package = build_analysis_package(
        provider,
        symbol,
        breadth_context_override=_build_breadth_context_override(context),
    )
    analysis_data = analysis_package.to_dict()
    trade_plan_warnings: list[str] = []

    try:
        trade_plan_data = generate_trade_plan(analysis_data)
    except Exception as exc:
        trade_plan_warnings.append(
            f"trade_plan generation failed; degraded fallback used: {type(exc).__name__}: {exc}"
        )
        trade_plan_data = _build_degraded_trade_plan(symbol, trade_plan_warnings[-1])

    try:
        markdown_text = render_trade_plan(analysis_package)
    except Exception as exc:
        trade_plan_warnings.append(
            f"trade_plan render failed; degraded markdown used: {type(exc).__name__}: {exc}"
        )
        markdown_text = _render_degraded_trade_plan_markdown(symbol, trade_plan_data)

    report_path = context.report_dir / f"trade_plan_{symbol.lower()}.md"
    export_result = export_markdown_report(
        analysis_package=analysis_package,
        markdown_text=markdown_text,
        output_path=str(report_path),
    )

    warnings, degraded_mode = _build_analysis_warnings(analysis_package)
    warnings.extend(trade_plan_warnings)
    warnings.extend(export_result.warnings)
    if bool(trade_plan_data.get("degraded_mode", False)):
        degraded_mode = True
        warnings.append("trade_plan degraded_mode enabled")

    manifest = create_manifest(
        symbols=[symbol],
        mode=context.mode,
        source_used=provider.provider_name(),
        files_created=list(export_result.files_created),
        warnings=list(warnings),
        errors=list(export_result.errors),
        duration_seconds=0.0,
        data_quality_summary={
            **dict(export_result.data_quality_summary),
            "degraded_mode": degraded_mode,
            "market_overview_loaded": context.market_overview_path is not None,
            "market_overview_path": context.market_overview_path or "",
        },
    )

    manifest_path = context.manifest_dir / f"manifest_{symbol.lower()}_{manifest.run_id}.json"
    saved_manifest_path = save_manifest(manifest, str(manifest_path))

    return SymbolRunResult(
        symbol=symbol,
        status="success",
        source_used=provider.provider_name(),
        fallback_used=False,
        degraded_mode=degraded_mode,
        warnings=warnings,
        errors=list(export_result.errors),
        files_created=list(export_result.files_created) + [saved_manifest_path],
        manifest_path=saved_manifest_path,
        report_path=str(report_path),
        analysis_data=analysis_data,
        trade_plan_data=trade_plan_data,
    )


def load_runtime_config(config_dir: Path) -> RuntimeConfigBundle:
    _log_step_start("load_runtime_config")
    runtime_config = _load_yaml(config_dir / "runtime.yaml")
    sources_config = _load_yaml(config_dir / "sources.yaml")
    runtime_config, sources_config = _apply_env_overrides(runtime_config, sources_config)

    bundle = RuntimeConfigBundle(
        config_dir=config_dir,
        runtime=runtime_config,
        sources=sources_config,
        watchlist=_load_yaml(config_dir / "watchlist.yaml", default={"symbols": []}),
        universe=_load_yaml(config_dir / "universe.yaml", default={}),
    )
    _log_step_end_with_counts("load_runtime_config")
    return bundle


def build_run_context(runtime_bundle: RuntimeConfigBundle) -> RunContext:
    _log_step_start("build_run_context")
    report_dir, manifest_dir = _output_dirs(runtime_bundle.runtime)
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    primary_provider, fallback_provider = _provider_names(runtime_bundle.sources)
    context = RunContext(
        run_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        started_at=time.perf_counter(),
        mode=_mode(runtime_bundle.runtime),
        selection_mode=_selection_mode(runtime_bundle.runtime),
        report_dir=report_dir,
        manifest_dir=manifest_dir,
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    logging.info("run_id=%s", context.run_id)
    logging.info("mode=%s", context.mode)
    logging.info("selection_mode=%s", context.selection_mode)
    logging.info("report_dir=%s", context.report_dir)
    logging.info("manifest_dir=%s", context.manifest_dir)
    logging.info("primary_provider=%s", context.primary_provider)
    logging.info("fallback_provider=%s", context.fallback_provider)
    _log_step_end_with_counts("build_run_context")
    return context


def load_market_overview_if_enabled(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("load_market_overview_if_enabled")
    try:
        if not _market_overview_enabled(runtime_bundle.runtime):
            return

        try:
            from scripts.build_market_overview import main as build_market_overview_main

            build_market_overview_main()
        except Exception as exc:
            _log_error("load_market_overview_if_enabled", exc)
            _warn_step(context, "load_market_overview_if_enabled", f"market_overview build failed: {type(exc).__name__}: {exc}")

        if not MARKET_OVERVIEW_PATH.exists():
            _warn_step(context, "load_market_overview_if_enabled", f"market_overview missing: {MARKET_OVERVIEW_PATH}")
            return

        payload = json.loads(MARKET_OVERVIEW_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            _warn_step(context, "load_market_overview_if_enabled", "market_overview payload is not a JSON object.")
            return

        context.market_overview = payload
        context.market_overview_path = str(MARKET_OVERVIEW_PATH)
        logging.info("market_overview_path=%s", context.market_overview_path)
    except Exception as exc:
        _log_error("load_market_overview_if_enabled", exc)
        _warn_step(context, "load_market_overview_if_enabled", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts(
            "load_market_overview_if_enabled",
            market_overview_loaded=1 if context.market_overview_path else 0,
        )


def scan_universe(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("scan_universe")
    try:
        _ = runtime_bundle
        if context.selection_mode != "top_from_universe":
            logging.info("scan_universe skipped because selection_mode=%s", context.selection_mode)
            return

        from scripts.universe_scan import main as universe_scan_main

        universe_scan_main()

        raw_scan_df = _load_dataframe(RAW_SCAN_OUTPUT_PATH)
        context.total_scanned = len(raw_scan_df)

        if not RAW_SCAN_OUTPUT_PATH.exists():
            _warn_step(context, "scan_universe", f"raw scan output missing after scan: {RAW_SCAN_OUTPUT_PATH}")
        if not RANKING_TABLE_PATH.exists():
            _warn_step(context, "scan_universe", f"ranking output missing after scan: {RANKING_TABLE_PATH}")
        if not TOP_SYMBOLS_PATH.exists():
            _warn_step(context, "scan_universe", f"top symbols output missing after scan: {TOP_SYMBOLS_PATH}")
    except Exception as exc:
        _log_error("scan_universe", exc)
        _warn_step(context, "scan_universe", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("scan_universe", total_scanned=context.total_scanned)


def rank_candidates(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("rank_candidates")
    try:
        _ = runtime_bundle
        ranking_df = _normalize_ranking_dataframe(_load_dataframe(RANKING_TABLE_PATH))
        if not ranking_df.empty:
            if "score" not in ranking_df.columns:
                _warn(context, "ranking output missing score column; attempting heuristic fallback.")
                ranking_df = pd.DataFrame()
            else:
                score_series = pd.to_numeric(ranking_df["score"], errors="coerce")
                missing_score_mask = score_series.isna()
                if bool(missing_score_mask.any()):
                    dropped_symbols = ranking_df.loc[missing_score_mask, "symbol"].astype(str).tolist()
                    ranking_df = ranking_df.loc[~missing_score_mask].reset_index(drop=True)
                    for dropped_symbol in dropped_symbols:
                        _warn(context, f"ranking missing score; dropped symbol={dropped_symbol}")
                    if not ranking_df.empty:
                        ranking_df["rank"] = range(1, len(ranking_df) + 1)

        if not ranking_df.empty:
            context.ranking_table = ranking_df
            context.ranking_source = str(RANKING_TABLE_PATH)
            context.total_ranked = len(ranking_df)
            _synthesize_market_overview_from_ranking(context)
            logging.info("ranking rows=%s source=%s", len(ranking_df), context.ranking_source)
            return

        raw_scan_df = _load_dataframe(RAW_SCAN_OUTPUT_PATH)
        fallback_ranking_df = _build_ranking_from_raw_scan(raw_scan_df)
        if not fallback_ranking_df.empty:
            score_series = pd.to_numeric(fallback_ranking_df.get("score"), errors="coerce")
            missing_score_mask = score_series.isna()
            if bool(missing_score_mask.any()):
                dropped_symbols = fallback_ranking_df.loc[missing_score_mask, "symbol"].astype(str).tolist()
                fallback_ranking_df = fallback_ranking_df.loc[~missing_score_mask].reset_index(drop=True)
                for dropped_symbol in dropped_symbols:
                    _warn(context, f"heuristic ranking missing score; dropped symbol={dropped_symbol}")
                if not fallback_ranking_df.empty:
                    fallback_ranking_df["rank"] = range(1, len(fallback_ranking_df) + 1)

        if not fallback_ranking_df.empty:
            context.ranking_table = fallback_ranking_df
            context.ranking_source = str(RAW_SCAN_OUTPUT_PATH)
            context.ranking_fallback_used = True
            context.total_ranked = len(fallback_ranking_df)
            _synthesize_market_overview_from_ranking(context)
            _warn_step(context, "rank_candidates", "fell back to usable raw scan data.")
            return

        _warn_step(context, "rank_candidates", "could not build ranking data.")
    except Exception as exc:
        _log_error("rank_candidates", exc)
        _warn_step(context, "rank_candidates", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("rank_candidates", ranked=context.total_ranked)


def select_top_symbols(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("select_top_symbols")
    try:
        top_n = int(runtime_bundle.runtime.get("selection", {}).get("top_n", 10))
        fallback_to_watchlist = bool(runtime_bundle.runtime.get("selection", {}).get("fallback_to_watchlist", False))

        if context.selection_mode == "watchlist":
            context.symbols_selected = _load_watchlist_symbols(runtime_bundle.watchlist)[:top_n]
            context.selection_source = "watchlist"
            context.total_selected = len(context.symbols_selected)
            if not context.symbols_selected:
                _warn_step(context, "select_top_symbols", "watchlist selection mode but watchlist is empty.")
                return
            if not context.ranking_table.empty:
                context.ranking_table = context.ranking_table[
                    context.ranking_table["symbol"].astype(str).str.upper().isin(context.symbols_selected)
                ].copy().reset_index(drop=True)
                if not context.ranking_table.empty:
                    context.ranking_table["rank"] = range(1, len(context.ranking_table) + 1)
            return

        top_symbols_path = _resolve_top_symbols_path(runtime_bundle.runtime)
        if top_symbols_path.exists():
            try:
                context.symbols_selected = _load_json_symbol_list(top_symbols_path)[:top_n]
                context.selection_source = str(top_symbols_path)
            except Exception as exc:
                _log_error("select_top_symbols", exc)
                _warn_step(context, "select_top_symbols", f"top symbols load failed: {type(exc).__name__}: {exc}")

        if not context.symbols_selected and not context.ranking_table.empty:
            context.symbols_selected = context.ranking_table.head(top_n)["symbol"].astype(str).tolist()
            context.selection_source = context.ranking_source or "ranking"
            context.selection_fallback_used = True
            _warn_step(context, "select_top_symbols", "fell back to ranking table.")

        if not context.symbols_selected and fallback_to_watchlist:
            context.symbols_selected = _load_watchlist_symbols(runtime_bundle.watchlist)[:top_n]
            context.selection_source = "watchlist"
            context.selection_fallback_used = True
            _warn_step(context, "select_top_symbols", "fell back to watchlist.")

        if not context.symbols_selected:
            _warn_step(context, "select_top_symbols", "produced empty symbol list.")
            return

        if not context.ranking_table.empty:
            context.ranking_table = context.ranking_table[
                context.ranking_table["symbol"].isin(context.symbols_selected)
            ].copy().reset_index(drop=True)
            if not context.ranking_table.empty:
                context.ranking_table["rank"] = range(1, len(context.ranking_table) + 1)

        context.total_selected = len(context.symbols_selected)
        logging.info("symbols_selected=%s", context.symbols_selected)
        logging.info("selection_source=%s", context.selection_source)
        logging.info("selection_fallback_used=%s", context.selection_fallback_used)
    except Exception as exc:
        _log_error("select_top_symbols", exc)
        _warn_step(context, "select_top_symbols", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("select_top_symbols", selected=context.total_selected)


def build_deep_dive_for_symbols(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("build_deep_dive_for_symbols")
    try:
        if not context.symbols_selected:
            _warn_step(context, "build_deep_dive_for_symbols", "skipped because symbols_selected is empty.")
            return

        symbol_delay_seconds = _deep_dive_symbol_delay_seconds(runtime_bundle.runtime)

        for index, symbol in enumerate(context.symbols_selected):
            logging.info("symbol=%s | deep_dive start", symbol)
            try:
                result = _build_symbol_artifacts(
                    context=context,
                    symbol=symbol,
                    provider_name=context.primary_provider,
                    runtime_bundle=runtime_bundle,
                )
            except BaseException as primary_exc:
                _re_raise_if_keyboard_interrupt(primary_exc)
                logging.error(
                    "step=build_deep_dive_for_symbols | symbol=%s | %s: %s",
                    symbol,
                    type(primary_exc).__name__,
                    primary_exc,
                )
                if context.fallback_provider and context.fallback_provider != context.primary_provider:
                    try:
                        result = _build_symbol_artifacts(
                            context=context,
                            symbol=symbol,
                            provider_name=context.fallback_provider,
                            runtime_bundle=runtime_bundle,
                        )
                        result.fallback_used = True
                        result.warnings.insert(
                            0,
                            f"primary provider failed; fallback used: {context.primary_provider} -> {context.fallback_provider}",
                        )
                    except BaseException as fallback_exc:
                        _re_raise_if_keyboard_interrupt(fallback_exc)
                        logging.error(
                            "step=build_deep_dive_for_symbols | symbol=%s | fallback | %s: %s",
                            symbol,
                            type(fallback_exc).__name__,
                            fallback_exc,
                        )
                        result = SymbolRunResult(
                            symbol=symbol,
                            status="failed",
                            source_used=context.fallback_provider,
                            fallback_used=True,
                            degraded_mode=False,
                            errors=[
                                f"primary provider error: {type(primary_exc).__name__}: {primary_exc}",
                                f"fallback provider error: {type(fallback_exc).__name__}: {fallback_exc}",
                            ],
                        )
                else:
                    result = SymbolRunResult(
                        symbol=symbol,
                        status="failed",
                        source_used=context.primary_provider,
                        fallback_used=False,
                        degraded_mode=False,
                        errors=[f"primary provider error: {type(primary_exc).__name__}: {primary_exc}"],
                    )

            context.symbol_results.append(result)
            context.files_created.extend(result.files_created)

            for warning in result.warnings:
                _warn(context, f"symbol={symbol} warning: {warning}")
            if result.errors:
                _warn_symbol(context, symbol, f"errors: {'; '.join(result.errors)}")

            if result.analysis_data:
                context.deep_dive_payloads[symbol] = result.analysis_data

            if result.status == "success":
                context.deep_dives_built += 1

            logging.info(
                "symbol=%s | deep_dive done | status=%s | report=%s | manifest=%s",
                symbol,
                result.status,
                result.report_path,
                result.manifest_path,
            )
            if symbol_delay_seconds > 0 and index < len(context.symbols_selected) - 1:
                logging.info("symbol=%s | throttling next deep_dive for %.1f seconds", symbol, symbol_delay_seconds)
                time.sleep(symbol_delay_seconds)
    except Exception as exc:
        _log_error("build_deep_dive_for_symbols", exc)
        _warn_step(context, "build_deep_dive_for_symbols", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("build_deep_dive_for_symbols", deep_dives_built=context.deep_dives_built)


def build_trade_plans(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("build_trade_plans")
    try:
        _ = runtime_bundle
        for result in context.symbol_results:
            if result.status == "success" and result.trade_plan_data:
                context.trade_plan_payloads[result.symbol] = result.trade_plan_data
        context.trade_plans_built = len(context.trade_plan_payloads)
    except Exception as exc:
        _log_error("build_trade_plans", exc)
        _warn_step(context, "build_trade_plans", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("build_trade_plans", trade_plans_built=context.trade_plans_built)


def compose_daily_briefing(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("compose_daily_briefing")
    try:
        _ = runtime_bundle
        context.daily_briefing_payload = build_daily_briefing(
            run_id=context.run_id,
            selection_mode=context.selection_mode,
            market_overview=context.market_overview or {},
            ranking_table=context.ranking_table.copy(),
            symbol_payloads=context.deep_dive_payloads,
            trade_plan_payloads=context.trade_plan_payloads,
            symbol_results=_serialize_symbol_results(context.symbol_results),
            warnings=list(context.job_warnings),
        )
        logging.info("daily_briefing_headline=%s", context.daily_briefing_payload.get("headline"))
    except Exception as exc:
        _log_error("compose_daily_briefing", exc)
        _warn_step(context, "compose_daily_briefing", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts(
            "compose_daily_briefing",
            opportunities=len(context.daily_briefing_payload.get("top_opportunities", [])),
        )


def compose_ai_briefing(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("compose_ai_briefing")
    try:
        _ = runtime_bundle
        ai_config = load_ai_analysis_config()
        if not ai_analysis_ready(ai_config):
            logging.info("AI analysis disabled or not configured. Skipping compose_ai_briefing.")
            return

        context.ai_analysis_payload = build_ai_daily_briefing(
            config=ai_config,
            base_briefing=context.daily_briefing_payload,
            market_overview=context.market_overview or {},
            symbol_payloads=context.deep_dive_payloads,
            trade_plan_payloads=context.trade_plan_payloads,
            warnings=list(context.job_warnings),
        )
        if context.ai_analysis_payload.get("headline"):
            context.daily_briefing_payload["headline"] = context.ai_analysis_payload["headline"]
        context.daily_briefing_payload["ai_analysis"] = dict(context.ai_analysis_payload)
        context.daily_briefing_payload["terminal_orchestration"] = build_terminal_orchestration(
            market_overview=context.market_overview or {},
            ranking_available=not context.ranking_table.empty,
            top_opportunities=context.daily_briefing_payload.get("top_opportunities", []),
            symbol_payloads=context.deep_dive_payloads,
            trade_plan_payloads=context.trade_plan_payloads,
            execution_status=context.daily_briefing_payload.get("execution_status", {}),
            skill_pipeline=context.daily_briefing_payload.get("skill_pipeline", {}),
            ai_analysis=context.ai_analysis_payload,
        )
        context.daily_briefing_payload["chief_analysis"] = build_chief_analysis(
            synthesis=context.daily_briefing_payload.get("market_synthesis", {}),
            generated_at=context.run_id,
            ai_analysis=context.ai_analysis_payload,
        )
        logging.info("ai_briefing_model=%s", context.ai_analysis_payload.get("model"))
    except Exception as exc:
        _log_error("compose_ai_briefing", exc)
        _warn_step(context, "compose_ai_briefing", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts(
            "compose_ai_briefing",
            ai_actions=len(context.ai_analysis_payload.get("action_plan", [])),
        )


def export_reports(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("export_reports")
    try:
        _ = runtime_bundle
        successful_results = [item for item in context.symbol_results if item.status == "success"]
        ranking_df = context.ranking_table.copy()
        if ranking_df.empty:
            ranking_df = _normalize_ranking_dataframe(pd.DataFrame([
                {
                    "symbol": item.symbol,
                    "score": item.analysis_data.get("score", ""),
                    "trend": item.analysis_data.get("trend", ""),
                    "momentum": item.analysis_data.get("momentum", ""),
                    "setup_type": item.trade_plan_data.get("setup_type", ""),
                    "risk_reward": item.trade_plan_data.get("risk_reward", ""),
                }
                for item in successful_results
            ]))

        export_result = export_report_bundle(
            run_id=context.run_id,
            market_overview=context.market_overview or {},
            ranking_table=ranking_df,
            deep_dives=context.deep_dive_payloads,
            trade_plans=context.trade_plan_payloads,
            daily_briefing=context.daily_briefing_payload,
            run_summary={
                "run_id": context.run_id,
                "generated_at": datetime.now().isoformat(),
                "total_input_symbols": len(context.symbols_selected),
                "total_analyzed": len(successful_results),
                "top_10_selected": context.symbols_selected[:10],
                "duration": round(time.perf_counter() - context.started_at, 2),
                "errors": [
                    f"{item.symbol}: {'; '.join(item.errors)}"
                    for item in context.symbol_results
                    if item.errors
                ],
            },
            warnings=list(context.job_warnings),
        )

        context.files_created.extend(export_result.files_created)
        context.bundle_output_dir = export_result.output_dir
        context.bundle_manifest_path = export_result.manifest_path

        logging.info("bundle_output_dir=%s", context.bundle_output_dir)
        logging.info("bundle_manifest_path=%s", context.bundle_manifest_path)
        if export_result.market_overview_path:
            logging.info("market_overview_report=%s", export_result.market_overview_path)
        if export_result.ranking_table_path:
            logging.info("ranking_report=%s", export_result.ranking_table_path)
        if export_result.daily_briefing_path:
            logging.info("daily_briefing_report=%s", export_result.daily_briefing_path)
        if export_result.market_analysis_report_path:
            logging.info("market_analysis_report=%s", export_result.market_analysis_report_path)
        if export_result.run_summary_path:
            logging.info("run_summary_report=%s", export_result.run_summary_path)

        for warning in export_result.warnings:
            _warn_step(context, "export_reports", f"warning: {warning}")
    except Exception as exc:
        _log_error("export_reports", exc)
        _warn_step(context, "export_reports", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts(
            "export_reports",
            files_exported=len(context.files_created),
        )


def write_manifest(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("write_manifest")
    try:
        _ = runtime_bundle
        if context.bundle_manifest_path:
            logging.info("manifest_path=%s", context.bundle_manifest_path)
        else:
            _warn_step(context, "write_manifest", "could not find bundle manifest path.")
    except Exception as exc:
        _log_error("write_manifest", exc)
        _warn_step(context, "write_manifest", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("write_manifest")


def build_final_summary(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> DictStrAny:
    _ = runtime_bundle
    duration_seconds = round(time.perf_counter() - context.started_at, 2)
    source_used_values = sorted({item.source_used for item in context.symbol_results if item.source_used})
    if not source_used_values:
        source_used = context.primary_provider
    elif len(source_used_values) == 1:
        source_used = source_used_values[0]
    else:
        source_used = ", ".join(source_used_values)

    total_candidates = len(context.ranking_table) if not context.ranking_table.empty else len(context.symbols_selected)
    market_overview_fallback_used = _market_overview_enabled(runtime_bundle.runtime) and context.market_overview is None

    summary = {
        "run_id": context.run_id,
        "headline": context.daily_briefing_payload.get("headline"),
        "chief_analysis": dict(context.daily_briefing_payload.get("chief_analysis", {})),
        "market_synthesis": dict(context.daily_briefing_payload.get("market_synthesis", {})),
        "selection_mode": context.selection_mode,
        "market_view": dict(context.daily_briefing_payload.get("market_view", {})),
        "vnindex_context": dict(context.daily_briefing_payload.get("vnindex_context", {})),
        "news_impact": dict(context.daily_briefing_payload.get("news_impact", {})),
        "long_candidates": dict(context.daily_briefing_payload.get("long_candidates", {})),
        "entry_execution": dict(context.daily_briefing_payload.get("entry_execution", {})),
        "top_opportunities": list(context.daily_briefing_payload.get("top_opportunities", [])),
        "symbols_selected": list(context.symbols_selected),
        "total": total_candidates,
        "success": sum(1 for item in context.symbol_results if item.status == "success"),
        "failed": sum(1 for item in context.symbol_results if item.status == "failed"),
        "warnings": list(context.job_warnings),
        "duration_seconds": duration_seconds,
        "source_used": source_used,
        "fallback_used": (
            context.ranking_fallback_used
            or context.selection_fallback_used
            or market_overview_fallback_used
            or any(item.fallback_used or item.degraded_mode for item in context.symbol_results)
        ),
        "manifest_path": context.bundle_manifest_path,
        "files_created": list(context.files_created),
        "exported_file_count": len(context.files_created),
        "total_scanned": context.total_scanned,
        "ranked": context.total_ranked,
        "selected": context.total_selected,
        "deep_dives_built": context.deep_dives_built,
        "trade_plans_built": context.trade_plans_built,
        "next_actions": list(context.daily_briefing_payload.get("next_actions", [])),
        "execution_quality": context.daily_briefing_payload.get("execution_status", {}).get("quality", "unknown"),
        "ai_headline": context.ai_analysis_payload.get("headline"),
        "ai_action_plan": list(context.ai_analysis_payload.get("action_plan", [])),
        "ai_market_story": context.ai_analysis_payload.get("market_story"),
        "ai_enabled": bool(context.ai_analysis_payload),
        "terminal_mode": context.daily_briefing_payload.get("terminal_orchestration", {}).get("mode"),
        "terminal_summary": context.daily_briefing_payload.get("terminal_orchestration", {}).get("summary"),
    }

    if context.bundle_output_dir:
        summary["artifacts_output_dir"] = context.bundle_output_dir

    return summary


def _build_notification_summary_text(summary: DictStrAny) -> str:
    return "\n".join(
        [
            "DAILY RUN NOTIFICATION",
            f"run_id={summary.get('run_id')}",
            f"selection_mode={summary.get('selection_mode')}",
            f"symbols_selected={summary.get('symbols_selected')}",
            f"total={summary.get('total')}",
            f"success={summary.get('success')}",
            f"failed={summary.get('failed')}",
            f"warnings={len(summary.get('warnings', []))}",
            f"duration_seconds={summary.get('duration_seconds')}",
            f"source_used={summary.get('source_used')}",
            f"fallback_used={summary.get('fallback_used')}",
            f"manifest_path={summary.get('manifest_path')}",
            f"output_dir={summary.get('artifacts_output_dir')}",
        ]
    )


def _send_console_notification(summary: DictStrAny) -> None:
    logging.info(_build_notification_summary_text(summary))


def send_notification(runtime_bundle: RuntimeConfigBundle, context: RunContext) -> None:
    _log_step_start("send_notification")
    payload = build_final_summary(runtime_bundle, context)
    try:
        if not _telegram_enabled(runtime_bundle.runtime):
            logging.info("Telegram notifier disabled by config. Skipping notification.")
            return

        telegram_config = _telegram_config(runtime_bundle.runtime)
        notifier = TelegramNotifier(
            bot_token=str(telegram_config.get("bot_token", "")).strip(),
            chat_id=str(telegram_config.get("chat_id", "")).strip(),
            enabled=bool(telegram_config.get("enabled", False)),
        )
        messages = build_daily_summary_messages(payload)
        if not messages:
            messages = [build_daily_summary_message(payload)]

        if notifier.send_messages(messages):
            logging.info("Telegram notification sent successfully.")
        else:
            _warn_step(context, "send_notification", "telegram notification failed.")
    except Exception as exc:
        _log_error("send_notification", exc)
        _warn_step(context, "send_notification", f"failed: {type(exc).__name__}: {exc}")
    finally:
        _log_step_end_with_counts("send_notification")


def main() -> DictStrAny:
    configure_logging()
    load_dotenv_if_present()
    args = parse_args()
    runtime_bundle = load_runtime_config(Path(args.config_dir).resolve())
    context = build_run_context(runtime_bundle)

    try:
        load_market_overview_if_enabled(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected load_market_overview_if_enabled error: {type(exc).__name__}: {exc}")

    try:
        scan_universe(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected scan_universe error: {type(exc).__name__}: {exc}")

    try:
        rank_candidates(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected rank_candidates error: {type(exc).__name__}: {exc}")

    try:
        select_top_symbols(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected select_top_symbols error: {type(exc).__name__}: {exc}")

    try:
        build_deep_dive_for_symbols(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected build_deep_dive_for_symbols error: {type(exc).__name__}: {exc}")

    try:
        build_trade_plans(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected build_trade_plans error: {type(exc).__name__}: {exc}")

    try:
        compose_daily_briefing(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected compose_daily_briefing error: {type(exc).__name__}: {exc}")

    try:
        compose_ai_briefing(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected compose_ai_briefing error: {type(exc).__name__}: {exc}")

    try:
        export_reports(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected export_reports error: {type(exc).__name__}: {exc}")

    try:
        write_manifest(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected write_manifest error: {type(exc).__name__}: {exc}")

    try:
        send_notification(runtime_bundle, context)
    except BaseException as exc:
        _re_raise_if_keyboard_interrupt(exc)
        _warn(context, f"unexpected send_notification error: {type(exc).__name__}: {exc}")

    summary = build_final_summary(runtime_bundle, context)

    logging.info(
        "\n".join(
            [
                "DAILY RUN SUMMARY",
                f"run_id={summary['run_id']}",
                f"selection_mode={summary['selection_mode']}",
                f"symbols_selected={summary['symbols_selected']}",
                f"total={summary['total']}",
                f"success={summary['success']}",
                f"failed={summary['failed']}",
                f"warnings={len(summary['warnings'])}",
                f"duration_seconds={summary['duration_seconds']}",
                f"source_used={summary['source_used']}",
                f"fallback_used={summary['fallback_used']}",
                f"total_scanned={summary['total_scanned']}",
                f"ranked={summary['ranked']}",
                f"selected={summary['selected']}",
                f"deep_dives_built={summary['deep_dives_built']}",
                f"trade_plans_built={summary['trade_plans_built']}",
                f"files_exported={summary['exported_file_count']}",
                f"output_dir={summary.get('artifacts_output_dir')}",
                f"manifest_path={summary['manifest_path']}",
            ]
        )
    )

    return summary


if __name__ == "__main__":
    print(main())
