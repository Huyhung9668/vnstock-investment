from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


DictStrAny = dict[str, Any]
DEFAULT_ARTIFACTS_DIR = Path("artifacts")


@dataclass(slots=True)
class ReportBundleExportResult:
    run_id: str
    generated_at: str
    output_dir: str
    manifest_path: str | None
    daily_briefing_path: str | None
    market_analysis_report_path: str | None
    run_summary_path: str | None
    market_overview_path: str | None
    ranking_table_path: str | None
    deep_dive_paths: list[str] = field(default_factory=list)
    trade_plan_paths: list[str] = field(default_factory=list)
    html_paths: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    total_symbols: int = 0
    exported_symbols: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)


def export_report_bundle(
    *,
    run_id: str | None = None,
    base_output_dir: str | Path = DEFAULT_ARTIFACTS_DIR,
    market_overview: dict[str, Any] | None = None,
    ranking_table: pd.DataFrame | list[dict[str, Any]] | None = None,
    deep_dives: dict[str, dict[str, Any]] | None = None,
    trade_plans: dict[str, dict[str, Any]] | None = None,
    daily_briefing: dict[str, Any] | None = None,
    run_summary: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ReportBundleExportResult:
    normalized_run_id = _normalize_run_id(run_id)
    output_dir = Path(base_output_dir) / normalized_run_id
    deep_dives_dir = output_dir / "deep_dives"
    trade_plans_dir = output_dir / "trade_plans"

    output_dir.mkdir(parents=True, exist_ok=True)
    deep_dives_dir.mkdir(parents=True, exist_ok=True)
    trade_plans_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now().isoformat()
    normalized_market_overview = _normalize_dict(market_overview)
    normalized_ranking = _normalize_ranking_table(ranking_table)
    normalized_deep_dives = _normalize_symbol_mapping(deep_dives)
    normalized_trade_plans = _normalize_symbol_mapping(trade_plans)
    normalized_daily_briefing = _normalize_dict(daily_briefing)
    normalized_run_summary = _normalize_dict(run_summary)
    collected_warnings = _normalize_string_list(warnings)
    files_created: list[str] = []

    exported_symbol_list = _collect_exported_symbols(
        ranking_table=normalized_ranking,
        deep_dives=normalized_deep_dives,
        trade_plans=normalized_trade_plans,
    )
    total_symbols = len(exported_symbol_list)

    market_content = _build_market_overview_content(
        market_overview=normalized_market_overview,
        generated_at=generated_at,
        warnings=collected_warnings,
    )
    market_overview_markdown, market_overview_html = _safe_write_content_pair(
        markdown_path=output_dir / "market_overview.md",
        html_path=output_dir / "market_overview.html",
        content=market_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="market_overview",
    )

    ranking_content = _build_ranking_content(normalized_ranking)
    ranking_top10_markdown, ranking_top10_html = _safe_write_content_pair(
        markdown_path=output_dir / "ranking_top10.md",
        html_path=output_dir / "ranking_top10.html",
        content=ranking_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="ranking_top10",
    )

    deep_dive_markdown_paths, deep_dive_html_map = _export_symbol_content_bundle(
        output_dir=deep_dives_dir,
        payloads=normalized_deep_dives,
        content_builder=_build_deep_dive_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="deep_dive",
    )

    trade_plan_markdown_paths, trade_plan_html_map = _export_symbol_content_bundle(
        output_dir=trade_plans_dir,
        payloads=normalized_trade_plans,
        content_builder=_build_trade_plan_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="trade_plan",
    )

    briefing_content = _build_daily_briefing_content(normalized_daily_briefing)
    daily_briefing_markdown, daily_briefing_html = _safe_write_content_pair(
        markdown_path=output_dir / "daily_briefing.md",
        html_path=output_dir / "daily_briefing.html",
        content=briefing_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="daily_briefing",
    )
    market_analysis_content = _build_market_analysis_report_content(normalized_daily_briefing)
    market_analysis_markdown, market_analysis_html = _safe_write_content_pair(
        markdown_path=output_dir / "market_analysis_report.md",
        html_path=output_dir / "market_analysis_report.html",
        content=market_analysis_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="market_analysis_report",
    )

    run_summary_payload = {
        **normalized_run_summary,
        "run_id": normalized_run_id,
        "generated_at": generated_at,
        "total_input_symbols": normalized_run_summary.get("total_input_symbols", total_symbols),
        "total_analyzed": normalized_run_summary.get("total_analyzed", total_symbols),
        "top_10_selected": normalized_run_summary.get("top_10_selected", exported_symbol_list[:10]),
        "total_exported_files": normalized_run_summary.get("total_exported_files", len(files_created) + 1),
    }
    run_summary_content = _build_run_summary_content(
        run_summary=run_summary_payload,
        warnings=collected_warnings,
    )
    run_summary_markdown, run_summary_html = _safe_write_content_pair(
        markdown_path=output_dir / "run_summary.md",
        html_path=output_dir / "run_summary.html",
        content=run_summary_content,
        files_created=files_created,
        warnings=collected_warnings,
        warning_prefix="run_summary",
    )

    manifest_file_path = output_dir / "manifest.json"
    manifest_payload = _build_manifest_payload(
        run_id=normalized_run_id,
        generated_at=generated_at,
        output_dir=output_dir,
        manifest_path=str(manifest_file_path),
        market_overview_markdown=market_overview_markdown,
        market_overview_html=market_overview_html,
        ranking_top10_markdown=ranking_top10_markdown,
        ranking_top10_html=ranking_top10_html,
        daily_briefing_markdown=daily_briefing_markdown,
        daily_briefing_html=daily_briefing_html,
        market_analysis_report_markdown=market_analysis_markdown,
        market_analysis_report_html=market_analysis_html,
        deep_dive_markdown_paths=deep_dive_markdown_paths,
        deep_dive_html_paths=_sorted_path_values(deep_dive_html_map),
        trade_plan_markdown_paths=trade_plan_markdown_paths,
        trade_plan_html_paths=_sorted_path_values(trade_plan_html_map),
        run_summary_markdown=run_summary_markdown,
        run_summary_html=run_summary_html,
        total_symbols=total_symbols,
        exported_symbols=len(exported_symbol_list),
        total_files_exported=len(files_created) + 1,
        warnings=collected_warnings,
    )

    manifest_path: str | None = None
    try:
        manifest_file_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_path = str(manifest_file_path)
        files_created.append(manifest_path)
    except Exception as exc:
        collected_warnings.append(f"manifest_json: {type(exc).__name__}: {exc}")

    return ReportBundleExportResult(
        run_id=normalized_run_id,
        generated_at=generated_at,
        output_dir=str(output_dir),
        manifest_path=manifest_path,
        daily_briefing_path=daily_briefing_markdown,
        market_analysis_report_path=market_analysis_markdown,
        run_summary_path=run_summary_markdown,
        market_overview_path=market_overview_markdown,
        ranking_table_path=ranking_top10_markdown,
        deep_dive_paths=deep_dive_markdown_paths,
        trade_plan_paths=trade_plan_markdown_paths,
        html_paths={
            "market_overview": market_overview_html,
            "ranking_top10": ranking_top10_html,
            "market_analysis_report": market_analysis_html,
            "deep_dives": deep_dive_html_map,
            "trade_plans": trade_plan_html_map,
            "run_summary": run_summary_html,
        },
        warnings=collected_warnings,
        total_symbols=total_symbols,
        exported_symbols=exported_symbol_list,
        files_created=files_created,
    )


def _normalize_run_id(run_id: str | None) -> str:
    if isinstance(run_id, str) and run_id.strip():
        return run_id.strip()
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _normalize_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _normalize_symbol_mapping(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        symbol = str(key).strip().upper()
        if not symbol:
            continue
        normalized[symbol] = dict(value) if isinstance(value, dict) else {"value": value}
    return normalized


def _normalize_ranking_table(payload: pd.DataFrame | list[dict[str, Any]] | None) -> pd.DataFrame:
    if isinstance(payload, pd.DataFrame):
        return payload.copy()
    if isinstance(payload, list):
        rows = [row for row in payload if isinstance(row, dict)]
        return pd.DataFrame(rows)
    return pd.DataFrame()


def _collect_exported_symbols(
    *,
    ranking_table: pd.DataFrame,
    deep_dives: dict[str, dict[str, Any]],
    trade_plans: dict[str, dict[str, Any]],
) -> list[str]:
    symbols: list[str] = []

    if not ranking_table.empty and "symbol" in ranking_table.columns:
        for symbol in ranking_table["symbol"].tolist():
            normalized_symbol = str(symbol).strip().upper()
            if normalized_symbol and normalized_symbol not in symbols:
                symbols.append(normalized_symbol)

    for symbol in list(deep_dives.keys()) + list(trade_plans.keys()):
        normalized_symbol = str(symbol).strip().upper()
        if normalized_symbol and normalized_symbol not in symbols:
            symbols.append(normalized_symbol)

    return symbols


def _build_market_overview_content(
    *,
    market_overview: dict[str, Any],
    generated_at: str,
    warnings: list[str],
) -> dict[str, Any]:
    regime = _ensure_dict(market_overview.get("regime"))
    breadth = _ensure_dict(market_overview.get("breadth"))
    index_context = _ensure_dict(market_overview.get("index_context"))
    sector_rotation = _records_to_dataframe(market_overview.get("sector_rotation"))

    key_catalysts = _normalize_string_list(market_overview.get("key_catalysts"))
    key_risks = _normalize_string_list(market_overview.get("market_risk_tags"))
    notable_themes = _normalize_string_list(market_overview.get("market_themes"))
    notes = _normalize_string_list(market_overview.get("notes"))

    if not market_overview:
        notes.append("Chưa có dữ liệu market overview, export ở chế độ degraded.")

    return {
        "title": "Market Overview",
        "sections": [
            {
                "title": "Overview",
                "items": [
                    ("generated_at", generated_at),
                    ("market_regime", regime.get("regime")),
                    ("market_overview", regime.get("explanation")),
                ],
            },
            {
                "title": "Breadth / Trend / Volatility",
                "items": [
                    ("breadth", breadth),
                    ("trend", index_context.get("avg_return_3m")),
                    ("volatility", index_context.get("volatility")),
                ],
            },
            {
                "title": "Key Catalysts",
                "bullets": key_catalysts or ["Chưa có key catalysts."],
            },
            {
                "title": "Key Risks",
                "bullets": key_risks or ["Chưa có key risks."],
            },
            {
                "title": "Notable Sectors / Themes",
                "bullets": notable_themes or _sector_rotation_labels(sector_rotation),
            },
            {
                "title": "Sector Rotation Table",
                "table": sector_rotation,
            },
            {
                "title": "Notes / Warnings",
                "bullets": notes + warnings if notes or warnings else ["Không có notes/warnings."],
            },
        ],
    }


def _build_ranking_content(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "title": "Ranking Top 10",
            "sections": [{"title": "Ranking", "bullets": ["Chưa có bảng xếp hạng để export."]}],
        }

    top_df = _ensure_dataframe_columns(
        df.head(10).copy(),
        [
            "rank",
            "symbol",
            "score",
            "trend",
            "momentum",
            "current_price",
            "support",
            "resistance",
            "setup_type",
            "risk_reward",
            "notes",
        ],
    )

    return {
        "title": "Ranking Top 10",
        "sections": [{"title": "Ranking", "table": top_df}],
    }


def _build_deep_dive_content(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    technical_summary = _extract_subset(
        payload,
        [
            "trend",
            "momentum",
            "current_price",
            "last_price",
            "support",
            "resistance",
            "atr",
            "volatility",
        ],
    )
    key_levels = {
        "current_price": payload.get("current_price") or payload.get("last_price"),
        "support": payload.get("support"),
        "resistance": payload.get("resistance"),
        "stop_loss": payload.get("stop_loss"),
        "target": payload.get("target"),
    }

    return {
        "title": f"Deep Dive: {symbol}",
        "sections": [
            {"title": "Symbol Header", "items": [("symbol", symbol)]},
            {"title": "Thesis", "items": [("thesis", payload.get("thesis"))]},
            {"title": "Technical Summary", "items": list(technical_summary.items())},
            {
                "title": "Catalysts",
                "bullets": _normalize_string_list(payload.get("catalysts")) or ["Chưa có catalysts."],
            },
            {
                "title": "Risks",
                "bullets": _normalize_string_list(payload.get("risks")) or ["Chưa có risks."],
            },
            {"title": "Key Levels", "items": list(key_levels.items())},
            {
                "title": "Scenario Notes",
                "bullets": _normalize_string_list(payload.get("scenario_notes")) or ["Chưa có scenario notes."],
            },
            {
                "title": "Data Quality Notes",
                "bullets": _normalize_string_list(payload.get("data_quality_notes"))
                or ["Chưa có data quality notes."],
            },
        ],
    }


def _build_trade_plan_content(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    entry_zone = _ensure_dict(payload.get("entry_zone"))
    target = _ensure_dict(payload.get("target"))

    return {
        "title": f"Trade Plan: {symbol}",
        "sections": [
            {"title": "Thesis", "items": [("thesis", payload.get("thesis"))]},
            {"title": "Setup Type", "items": [("setup_type", payload.get("setup_type"))]},
            {"title": "Entry Zone", "items": list(entry_zone.items()) or [("entry_zone", None)]},
            {
                "title": "Confirmation",
                "bullets": _normalize_string_list(payload.get("confirmation")) or ["Chưa có confirmation."],
            },
            {"title": "Invalidation", "items": [("invalidation", payload.get("invalidation"))]},
            {"title": "Target", "items": list(target.items()) or [("target", None)]},
            {"title": "Stop Loss", "items": [("stop_loss", payload.get("stop_loss"))]},
            {"title": "Risk Reward", "items": [("risk_reward", payload.get("risk_reward"))]},
            {
                "title": "Position Sizing Hint",
                "items": [("position_sizing_hint", payload.get("position_sizing_hint"))],
            },
            {
                "title": "Monitoring Checklist",
                "bullets": _normalize_string_list(payload.get("monitoring_checklist"))
                or ["Chưa có monitoring checklist."],
            },
            {
                "title": "Notes",
                "bullets": _normalize_string_list(payload.get("notes")) or ["Không có ghi chú bổ sung."],
            },
        ],
    }


def _build_daily_briefing_content(payload: dict[str, Any]) -> dict[str, Any]:
    market_view = _ensure_dict(payload.get("market_view"))
    execution_status = _ensure_dict(payload.get("execution_status"))
    ai_analysis = _ensure_dict(payload.get("ai_analysis"))
    market_synthesis = _ensure_dict(payload.get("market_synthesis"))
    chief_analysis = _ensure_dict(payload.get("chief_analysis"))
    skill_pipeline = _ensure_dict(payload.get("skill_pipeline"))
    normalized_runtime = _ensure_dict(payload.get("normalized_runtime"))
    news_context = _ensure_dict(payload.get("news_context"))
    top_opportunities = payload.get("top_opportunities")
    if not isinstance(top_opportunities, list):
        top_opportunities = []

    opportunity_rows = []
    for item in top_opportunities:
        if not isinstance(item, dict):
            continue
        opportunity_rows.append(
            {
                "symbol": item.get("symbol", ""),
                "setup_type": item.get("setup_type", ""),
                "trigger": item.get("trigger", ""),
                "risk_reward": item.get("risk_reward", ""),
                "degraded_mode": item.get("degraded_mode", False),
            }
        )

    ai_note_rows = []
    for item in ai_analysis.get("top_symbol_notes", []):
        if not isinstance(item, dict):
            continue
        ai_note_rows.append(
            {
                "symbol": item.get("symbol", ""),
                "note": item.get("note", ""),
            }
        )

    chief_sections: list[dict[str, Any]] = []
    for section in chief_analysis.get("sections", []):
        if not isinstance(section, dict):
            continue
        chief_sections.append(
            {
                "title": section.get("title"),
                "paragraphs": section.get("paragraphs"),
                "bullets": section.get("bullets"),
            }
        )

    synthesis_focus_rows = []
    for item in market_synthesis.get("top_stock_focus", []):
        if not isinstance(item, dict):
            continue
        synthesis_focus_rows.append(
            {
                "symbol": item.get("symbol", ""),
                "setup_type": item.get("setup_type", ""),
                "trigger": item.get("trigger", ""),
                "risk_reward": item.get("risk_reward", ""),
                "degraded_mode": item.get("degraded_mode", False),
            }
        )

    skill_stage_rows = []
    for name, stage in skill_pipeline.get("stages", {}).items():
        if not isinstance(stage, dict):
            continue
        skill_stage_rows.append(
            {
                "skill_stage": name,
                "status": stage.get("status", ""),
                "summary": stage.get("summary", ""),
            }
        )

    news_symbol_rows = []
    for symbol, summary in news_context.get("symbol_summaries", {}).items():
        if not isinstance(summary, dict):
            continue
        news_symbol_rows.append(
            {
                "symbol": symbol,
                "news_count": summary.get("news_count", 0),
                "news_signal": summary.get("news_signal", 0.0),
                "sentiment_summary": summary.get("sentiment_summary", ""),
                "catalyst_tags": ", ".join(_normalize_string_list(summary.get("catalyst_tags"))),
                "risk_tags": ", ".join(_normalize_string_list(summary.get("risk_tags"))),
            }
        )

    return {
        "title": chief_analysis.get("title") or "Daily Briefing",
        "sections": [
            {
                "title": "Headline",
                "items": [
                    ("run_id", payload.get("run_id")),
                    ("headline", payload.get("headline")),
                    ("selection_mode", payload.get("selection_mode")),
                    ("update_line", chief_analysis.get("update_line")),
                    ("stance", chief_analysis.get("stance")),
                    ("confidence", chief_analysis.get("confidence")),
                ],
            },
            {
                "title": "Executive Summary",
                "paragraphs": [chief_analysis.get("summary")] if chief_analysis.get("summary") else [],
            },
            *chief_sections,
            {
                "title": "Market Context",
                "items": [
                    ("summary", market_view.get("summary")),
                    ("regime", market_view.get("regime")),
                    ("breadth", market_view.get("breadth")),
                    ("volatility", market_view.get("volatility")),
                ],
            },
            {
                "title": "Execution Status",
                "items": list(execution_status.items()),
            },
            {
                "title": "AI Interpretation",
                "items": [
                    ("ai_headline", ai_analysis.get("headline")),
                    ("market_story", ai_analysis.get("market_story")),
                    ("portfolio_focus", ai_analysis.get("portfolio_focus")),
                    ("model", ai_analysis.get("model")),
                ],
            },
            {
                "title": "Top Opportunities",
                "table": pd.DataFrame(opportunity_rows),
            },
            {
                "title": "AI Notes By Symbol",
                "table": pd.DataFrame(ai_note_rows),
            },
            {
                "title": "Synthesis Focus Table",
                "table": pd.DataFrame(synthesis_focus_rows),
            },
            {
                "title": "Skill Pipeline Stages",
                "table": pd.DataFrame(skill_stage_rows),
            },
            {
                "title": "Runtime Normalization",
                "items": list(normalized_runtime.items()),
            },
            {
                "title": "News Context",
                "items": [
                    ("status", news_context.get("status")),
                    ("selected_symbol_count", news_context.get("selected_symbol_count")),
                    ("symbols_with_news_context", news_context.get("symbols_with_news_context")),
                    ("news_items_total", news_context.get("news_items_total")),
                    ("market_sentiment_summary", _ensure_dict(news_context.get("market_summary")).get("market_sentiment_summary")),
                ],
            },
            {
                "title": "News By Symbol",
                "table": pd.DataFrame(news_symbol_rows),
            },
            {
                "title": "Next Actions",
                "bullets": _normalize_string_list(payload.get("next_actions")) or ["Chua co next actions."],
            },
            {
                "title": "Synthesis Action Plan",
                "bullets": _normalize_string_list(market_synthesis.get("action_plan"))
                or ["Chua co synthesis action plan."],
            },
            {
                "title": "Synthesis Risk Watch",
                "bullets": _normalize_string_list(market_synthesis.get("risk_watch"))
                or ["Chua co synthesis risk watch."],
            },
            {
                "title": "AI Action Plan",
                "bullets": _normalize_string_list(ai_analysis.get("action_plan")) or ["AI chua de xuat hanh dong them."],
            },
            {
                "title": "AI Risk Alerts",
                "bullets": _normalize_string_list(ai_analysis.get("risk_alerts")) or ["AI chua co canh bao bo sung."],
            },
            {
                "title": "Warnings",
                "bullets": _normalize_string_list(payload.get("warnings")) or ["Khong co warning dang ke."],
            },
        ],
    }


def _build_market_analysis_report_content(payload: dict[str, Any]) -> dict[str, Any]:
    chief_analysis = _ensure_dict(payload.get("chief_analysis"))
    market_synthesis = _ensure_dict(payload.get("market_synthesis"))
    terminal_orchestration = _ensure_dict(payload.get("terminal_orchestration"))
    skill_pipeline = _ensure_dict(payload.get("skill_pipeline"))
    normalized_runtime = _ensure_dict(payload.get("normalized_runtime"))
    news_context = _ensure_dict(payload.get("news_context"))
    ai_analysis = _ensure_dict(payload.get("ai_analysis"))

    sections: list[dict[str, Any]] = [
        {
            "title": "Meta",
            "items": [
                ("run_id", payload.get("run_id")),
                ("headline", payload.get("headline")),
                ("selection_mode", payload.get("selection_mode")),
                ("update_line", chief_analysis.get("update_line")),
                ("terminal_mode", terminal_orchestration.get("mode")),
                ("terminal_summary", terminal_orchestration.get("summary")),
            ],
        },
        {
            "title": "Executive Summary",
            "paragraphs": [chief_analysis.get("summary")] if chief_analysis.get("summary") else [],
        },
    ]

    for section in chief_analysis.get("sections", []):
        if not isinstance(section, dict):
            continue
        sections.append(
            {
                "title": section.get("title"),
                "paragraphs": section.get("paragraphs"),
                "bullets": section.get("bullets"),
            }
        )

    stage_rows = []
    for stage in terminal_orchestration.get("stage_status", []):
        if not isinstance(stage, dict):
            continue
        stage_rows.append(
            {
                "name": stage.get("name", ""),
                "status": stage.get("status", ""),
                "enabled": stage.get("enabled", False),
                "description": stage.get("description", ""),
            }
        )

    focus_rows = []
    for item in market_synthesis.get("top_stock_focus", []):
        if not isinstance(item, dict):
            continue
        focus_rows.append(
            {
                "symbol": item.get("symbol", ""),
                "setup_type": item.get("setup_type", ""),
                "trigger": item.get("trigger", ""),
                "risk_reward": item.get("risk_reward", ""),
                "invalidation": item.get("invalidation", ""),
                "degraded_mode": item.get("degraded_mode", False),
            }
        )

    skill_stage_rows = []
    for name, stage in skill_pipeline.get("stages", {}).items():
        if not isinstance(stage, dict):
            continue
        skill_stage_rows.append(
            {
                "skill_stage": name,
                "status": stage.get("status", ""),
                "summary": stage.get("summary", ""),
            }
        )

    news_symbol_rows = []
    for symbol, summary in news_context.get("symbol_summaries", {}).items():
        if not isinstance(summary, dict):
            continue
        news_symbol_rows.append(
            {
                "symbol": symbol,
                "news_count": summary.get("news_count", 0),
                "news_signal": summary.get("news_signal", 0.0),
                "sentiment_summary": summary.get("sentiment_summary", ""),
            }
        )

    sections.extend(
        [
            {
                "title": "Runtime Normalization",
                "items": list(normalized_runtime.items()),
            },
            {
                "title": "Skill Pipeline Summary",
                "items": [
                    ("pipeline_status", skill_pipeline.get("status")),
                    ("completed_stage_count", skill_pipeline.get("completed_stage_count")),
                    ("total_stage_count", skill_pipeline.get("total_stage_count")),
                ],
            },
            {
                "title": "Skill Stage Outputs",
                "table": pd.DataFrame(skill_stage_rows),
            },
            {
                "title": "News Context",
                "items": [
                    ("status", news_context.get("status")),
                    ("selected_symbol_count", news_context.get("selected_symbol_count")),
                    ("symbols_with_news_context", news_context.get("symbols_with_news_context")),
                    ("news_items_total", news_context.get("news_items_total")),
                    ("market_sentiment_summary", _ensure_dict(news_context.get("market_summary")).get("market_sentiment_summary")),
                ],
            },
            {
                "title": "News Context By Symbol",
                "table": pd.DataFrame(news_symbol_rows),
            },
            {
                "title": "Top Focus Table",
                "table": pd.DataFrame(focus_rows),
            },
            {
                "title": "AI Overlay",
                "items": [
                    ("ai_headline", ai_analysis.get("headline")),
                    ("market_story", ai_analysis.get("market_story")),
                    ("portfolio_focus", ai_analysis.get("portfolio_focus")),
                    ("model", ai_analysis.get("model")),
                ],
            },
            {
                "title": "Terminal Stages",
                "table": pd.DataFrame(stage_rows),
            },
            {
                "title": "Warnings",
                "bullets": _normalize_string_list(payload.get("warnings")) or ["Khong co warning dang ke."],
            },
        ]
    )

    return {
        "title": chief_analysis.get("title") or "Market Analysis Report",
        "sections": sections,
    }


def _build_run_summary_content(*, run_summary: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    return {
        "title": "Run Summary",
        "sections": [
            {
                "title": "Overview",
                "items": [
                    ("run_id", run_summary.get("run_id")),
                    ("generated_at", run_summary.get("generated_at")),
                    ("total_input_symbols", run_summary.get("total_input_symbols")),
                    ("total_analyzed", run_summary.get("total_analyzed")),
                    ("top_10_selected", run_summary.get("top_10_selected")),
                    ("total_exported_files", run_summary.get("total_exported_files")),
                    ("duration", run_summary.get("duration")),
                ],
            },
            {
                "title": "Warnings / Errors",
                "bullets": warnings + _normalize_string_list(run_summary.get("errors"))
                if warnings or run_summary.get("errors")
                else ["Không có warning/error đáng chú ý."],
            },
        ],
    }


def _safe_write_content_pair(
    *,
    markdown_path: Path,
    html_path: Path,
    content: dict[str, Any],
    files_created: list[str],
    warnings: list[str],
    warning_prefix: str,
) -> tuple[str | None, str | None]:
    markdown_file: str | None = None
    html_file: str | None = None

    try:
        markdown_text = _render_markdown_from_content(content)
        markdown_path.write_text(markdown_text.strip() + "\n", encoding="utf-8")
        markdown_file = str(markdown_path)
        files_created.append(markdown_file)
    except Exception as exc:
        warnings.append(f"{warning_prefix}_markdown: {type(exc).__name__}: {exc}")

    try:
        html_text = _render_html_document(
            title=str(content.get("title", "Report")),
            body_html=_render_html_from_content(content),
        )
        html_path.write_text(html_text, encoding="utf-8")
        html_file = str(html_path)
        files_created.append(html_file)
    except Exception as exc:
        warnings.append(f"{warning_prefix}_html: {type(exc).__name__}: {exc}")

    return markdown_file, html_file


def _export_symbol_content_bundle(
    *,
    output_dir: Path,
    payloads: dict[str, dict[str, Any]],
    content_builder: Any,
    files_created: list[str],
    warnings: list[str],
    warning_prefix: str,
) -> tuple[list[str], dict[str, str]]:
    markdown_paths: list[str] = []
    html_paths: dict[str, str] = {}

    for symbol in sorted(payloads):
        content = content_builder(symbol, payloads[symbol])
        markdown_file, html_file = _safe_write_content_pair(
            markdown_path=output_dir / f"{symbol.lower()}.md",
            html_path=output_dir / f"{symbol.lower()}.html",
            content=content,
            files_created=files_created,
            warnings=warnings,
            warning_prefix=f"{warning_prefix}_{symbol.lower()}",
        )
        if markdown_file is not None:
            markdown_paths.append(markdown_file)
        if html_file is not None:
            html_paths[symbol] = html_file

    return markdown_paths, html_paths


def _build_manifest_payload(
    *,
    run_id: str,
    generated_at: str,
    output_dir: Path,
    manifest_path: str,
    market_overview_markdown: str | None,
    market_overview_html: str | None,
    ranking_top10_markdown: str | None,
    ranking_top10_html: str | None,
    daily_briefing_markdown: str | None,
    daily_briefing_html: str | None,
    market_analysis_report_markdown: str | None,
    market_analysis_report_html: str | None,
    deep_dive_markdown_paths: list[str],
    deep_dive_html_paths: list[str],
    trade_plan_markdown_paths: list[str],
    trade_plan_html_paths: list[str],
    run_summary_markdown: str | None,
    run_summary_html: str | None,
    total_symbols: int,
    exported_symbols: int,
    total_files_exported: int,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "generated_at": generated_at,
        "output_dir": str(output_dir),
        "manifest_path": manifest_path,
        "market_overview_markdown": market_overview_markdown,
        "market_overview_html": market_overview_html,
        "ranking_top10_markdown": ranking_top10_markdown,
        "ranking_top10_html": ranking_top10_html,
        "daily_briefing_markdown": daily_briefing_markdown,
        "daily_briefing_html": daily_briefing_html,
        "market_analysis_report_markdown": market_analysis_report_markdown,
        "market_analysis_report_html": market_analysis_report_html,
        "deep_dive_markdown_paths": deep_dive_markdown_paths,
        "deep_dive_html_paths": deep_dive_html_paths,
        "trade_plan_markdown_paths": trade_plan_markdown_paths,
        "trade_plan_html_paths": trade_plan_html_paths,
        "run_summary_markdown": run_summary_markdown,
        "run_summary_html": run_summary_html,
        "total_symbols": total_symbols,
        "exported_symbols": exported_symbols,
        "total_files_exported": total_files_exported,
        "warnings": warnings,
    }


def _sorted_path_values(path_map: dict[str, str]) -> list[str]:
    return [path_map[key] for key in sorted(path_map)]


def _render_markdown_from_content(content: dict[str, Any]) -> str:
    lines = [f"# {content.get('title', 'Report')}"]

    for section in content.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title", "")).strip()
        if title:
            lines.extend(["", f"## {title}"])

        items = section.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, tuple) and len(item) == 2:
                    lines.append(f"- `{item[0]}`: {_scalar_text(item[1])}")

        paragraphs = section.get("paragraphs")
        if isinstance(paragraphs, list):
            for paragraph in paragraphs:
                text = str(paragraph).strip()
                if text:
                    lines.append(text)

        bullets = section.get("bullets")
        if isinstance(bullets, list):
            for bullet in bullets:
                lines.append(f"- {bullet}")

        table = section.get("table")
        if isinstance(table, pd.DataFrame):
            lines.append(_dataframe_to_markdown(table))

    return "\n".join(lines).strip()


def _render_html_from_content(content: dict[str, Any]) -> str:
    html_parts = [f"<h1>{escape(str(content.get('title', 'Report')))}</h1>"]

    for section in content.get("sections", []):
        if not isinstance(section, dict):
            continue

        title = str(section.get("title", "")).strip()
        if title:
            html_parts.append(f"<h2>{escape(title)}</h2>")

        items = section.get("items")
        if isinstance(items, list):
            rows = [item for item in items if isinstance(item, tuple) and len(item) == 2]
            if rows:
                html_parts.append("<ul>")
                for key, value in rows:
                    html_parts.append(
                        f"<li><strong>{escape(str(key))}</strong>: {escape(_scalar_text(value))}</li>"
                    )
                html_parts.append("</ul>")

        paragraphs = section.get("paragraphs")
        if isinstance(paragraphs, list):
            for paragraph in paragraphs:
                text = str(paragraph).strip()
                if text:
                    html_parts.append(f"<p>{escape(text)}</p>")

        bullets = section.get("bullets")
        if isinstance(bullets, list) and bullets:
            html_parts.append("<ul>")
            for bullet in bullets:
                html_parts.append(f"<li>{escape(str(bullet))}</li>")
            html_parts.append("</ul>")

        table = section.get("table")
        if isinstance(table, pd.DataFrame):
            html_parts.append(_dataframe_to_html(table))

    return "".join(html_parts)


def _ensure_dataframe_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    working_df = df.copy()
    for column in columns:
        if column not in working_df.columns:
            working_df[column] = ""
    return working_df[columns]


def _records_to_dataframe(payload: Any) -> pd.DataFrame:
    if not isinstance(payload, list):
        return pd.DataFrame()
    rows = [row for row in payload if isinstance(row, dict)]
    return pd.DataFrame(rows)


def _sector_rotation_labels(df: pd.DataFrame) -> list[str]:
    if df.empty or "sector" not in df.columns:
        return ["Chưa có sectors/themes nổi bật."]

    labels: list[str] = []
    for _, row in df.head(5).iterrows():
        sector = str(row.get("sector", "")).strip()
        rotation_label = str(row.get("rotation_label", "")).strip()
        if sector:
            labels.append(f"{sector} ({rotation_label or 'neutral'})")
    return labels or ["Chưa có sectors/themes nổi bật."]


def _extract_subset(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}


def _ensure_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "- Chưa có dữ liệu bảng."
    try:
        return df.fillna("").to_markdown(index=False)
    except Exception:
        return _fallback_table_markdown(df.fillna(""))


def _dataframe_to_html(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p>Chưa có dữ liệu bảng.</p>"
    try:
        return df.fillna("").to_html(index=False, escape=True)
    except Exception:
        return "<pre>" + escape(_fallback_table_markdown(df.fillna(""))) + "</pre>"


def _fallback_table_markdown(df: pd.DataFrame) -> str:
    headers = [str(column) for column in df.columns]
    header_row = "| " + " | ".join(headers) + " |"
    divider_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = []
    for _, row in df.iterrows():
        body_rows.append("| " + " | ".join(_scalar_text(row[column]) for column in df.columns) + " |")
    return "\n".join([header_row, divider_row, *body_rows])


def _render_html_document(*, title: str, body_html: str) -> str:
    return (
        "<!doctype html>"
        "<html lang=\"vi\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title>"
        "<style>"
        "body{font-family:Arial,Helvetica,sans-serif;max-width:1100px;margin:32px auto;padding:0 16px;line-height:1.6;color:#1f2937;}"
        "table{border-collapse:collapse;width:100%;margin:16px 0;}"
        "th,td{border:1px solid #d1d5db;padding:8px;text-align:left;vertical-align:top;}"
        "th{background:#f3f4f6;}"
        "code{background:#f3f4f6;padding:2px 4px;border-radius:4px;}"
        "h1,h2,h3{color:#111827;}"
        "ul{padding-left:20px;}"
        "</style>"
        "</head>"
        "<body>"
        f"{body_html}"
        "</body>"
        "</html>"
    )


def _scalar_text(value: Any) -> str:
    if value is None:
        return "Chưa có dữ liệu"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "[]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
