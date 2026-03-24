from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.analysis_package import AnalysisPackage
from services.manifest_service import create_manifest, save_manifest
from services.report_exporter import export_markdown_report
from services.trade_plan_service import render_trade_plan


@pytest.fixture
def full_analysis_package() -> AnalysisPackage:
    return make_analysis_package()


@pytest.fixture
def degraded_analysis_package() -> AnalysisPackage:
    return make_analysis_package(missing_sections=["financial_summary", "news_summary"])


def make_analysis_package(*, missing_sections: list[str] | None = None) -> AnalysisPackage:
    missing = list(missing_sections or [])

    financial_summary = None if "financial_summary" in missing else {"revenue": 1000, "profit": 200}
    news_summary = None if "news_summary" in missing else {"article_count": 3, "latest": {"title": "Catalyst"}}
    breadth_context = None if "breadth_context" in missing else {"advance_decline": 1.2}

    return AnalysisPackage(
        symbol="FPT",
        company={"name": "FPT Corporation", "sector": "Technology"},
        price_summary={"close": 123.45, "change_pct": 1.2, "volume": 1000000},
        financial_summary=financial_summary,
        news_summary=news_summary,
        signals={"trend": "positive", "momentum": "improving"},
        risks={"event_risk": "medium"},
        breadth_context=breadth_context,
        data_quality={
            "provider_health": {"status": "ok"},
            "sections": {
                "company": {"status": "ok", "present": True},
                "price_summary": {"status": "ok", "present": True},
                "financial_summary": {"status": "missing" if financial_summary is None else "ok", "present": financial_summary is not None},
                "news_summary": {"status": "missing" if news_summary is None else "ok", "present": news_summary is not None},
                "breadth_context": {"status": "missing" if breadth_context is None else "ok", "present": breadth_context is not None},
            },
        },
        missing_sections=missing,
        provider_metadata={"provider_name": "free_provider"},
        generated_at=datetime(2026, 3, 23, 12, 0, 0),
    )


def test_markdown_report_contains_minimum_expected_sections(full_analysis_package: AnalysisPackage) -> None:
    markdown = render_trade_plan(full_analysis_package)

    assert "# Trade Plan: FPT" in markdown
    assert "## Tom tat du lieu dau vao" in markdown
    assert "## Price overview" in markdown
    assert "## Technical / trend" in markdown
    assert "## Financial snapshot" in markdown
    assert "## News / catalysts" in markdown
    assert "- Financial summary: co du lieu (financial_summary)" in markdown
    assert "- News summary: co du lieu (news_summary)" in markdown
    assert "## Scenario 1: Tich cuc" in markdown
    assert "## Scenario 2: Trung tinh" in markdown
    assert "## Scenario 3: Tieu cuc" in markdown
    assert "## Ket luan trung lap" in markdown


def test_missing_financial_and_news_sections_are_still_present_and_marked_unavailable(
    degraded_analysis_package: AnalysisPackage,
) -> None:
    markdown = render_trade_plan(degraded_analysis_package)

    assert "## Financial snapshot" in markdown
    assert "## News / catalysts" in markdown
    assert markdown.count("- Status: unavailable") >= 2
    assert "- Financial summary: thieu (financial_summary)" in markdown
    assert "- News summary: thieu (news_summary)" in markdown
    assert "## Canh bao thieu du lieu" in markdown
    assert "Thieu `financial_summary`" in markdown
    assert "Thieu `news_summary`" in markdown


def test_exported_markdown_contains_data_quality_section(tmp_path: Path, full_analysis_package: AnalysisPackage) -> None:
    markdown = render_trade_plan(full_analysis_package)
    output_path = tmp_path / "trade_plan_fpt.md"

    result = export_markdown_report(
        analysis_package=full_analysis_package,
        markdown_text=markdown,
        output_path=str(output_path),
    )

    saved_content = output_path.read_text(encoding="utf-8")
    assert result.output_path == str(output_path)
    assert "# Trade Plan: FPT" in saved_content
    assert "## Tom tat du lieu dau vao" in saved_content
    assert "## Price overview" in saved_content
    assert "## Financial snapshot" in saved_content
    assert "## News / catalysts" in saved_content
    assert "## Ket luan trung lap" in saved_content
    assert "## Data coverage / Data quality" in saved_content
    assert "- provider: `free_provider`" in saved_content


def test_manifest_files_created_matches_actual_output_file(tmp_path: Path, full_analysis_package: AnalysisPackage) -> None:
    markdown = render_trade_plan(full_analysis_package)
    report_path = tmp_path / "trade_plan_fpt.md"

    export_result = export_markdown_report(
        analysis_package=full_analysis_package,
        markdown_text=markdown,
        output_path=str(report_path),
    )
    manifest = create_manifest(
        symbols=["FPT"],
        mode="free",
        source_used="free_provider",
        files_created=export_result.files_created,
        warnings=export_result.warnings,
        errors=export_result.errors,
        duration_seconds=1.5,
        data_quality_summary=export_result.data_quality_summary,
    )
    manifest_path = tmp_path / "manifests" / "manifest.json"
    save_manifest(manifest, str(manifest_path))

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert report_path.exists()
    assert payload["files_created"] == [str(report_path)]
    assert payload["files_created"][0] == export_result.output_path
    assert Path(payload["files_created"][0]).exists()


def test_exporter_output_and_manifest_consistency_with_missing_optional_sections(
    tmp_path: Path,
    degraded_analysis_package: AnalysisPackage,
) -> None:
    markdown = render_trade_plan(degraded_analysis_package)
    report_path = tmp_path / "trade_plan_fpt.md"

    export_result = export_markdown_report(
        analysis_package=degraded_analysis_package,
        markdown_text=markdown,
        output_path=str(report_path),
    )
    manifest = create_manifest(
        symbols=["FPT"],
        mode="free",
        source_used="free_provider",
        files_created=export_result.files_created,
        warnings=export_result.warnings,
        errors=export_result.errors,
        duration_seconds=2.0,
        data_quality_summary=export_result.data_quality_summary,
    )

    assert export_result.files_created == [str(report_path)]
    assert export_result.data_quality_summary["overall_status"] == "medium"
    assert "Missing optional sections: `financial_summary`, `news_summary`" in export_result.warnings
    assert manifest.files_created == [str(report_path)]
