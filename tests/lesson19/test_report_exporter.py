from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from models.analysis_package import AnalysisPackage
from services.report_exporter import (
    build_data_quality_summary,
    ensure_data_quality_section,
    export_markdown_report,
)


@pytest.fixture
def base_analysis_package() -> AnalysisPackage:
    return make_analysis_package()


def make_analysis_package(
    *,
    missing_sections: list[str] | None = None,
    provider_health_status: str = "ok",
    generated_at: datetime | None = None,
) -> AnalysisPackage:
    missing = list(missing_sections or [])

    financial_summary = None if "financial_summary" in missing else {"revenue": 1000}
    news_summary = None if "news_summary" in missing else {"article_count": 5}
    breadth_context = None if "breadth_context" in missing else {"advance_decline": 1.1}

    section_statuses = {
        "company": {"status": "ok", "present": True, "record_count": 2},
        "price_summary": {"status": "ok", "present": True, "record_count": 3},
        "financial_summary": {
            "status": "missing" if financial_summary is None else "ok",
            "present": financial_summary is not None,
        },
        "news_summary": {
            "status": "missing" if news_summary is None else "ok",
            "present": news_summary is not None,
        },
        "breadth_context": {
            "status": "missing" if breadth_context is None else "ok",
            "present": breadth_context is not None,
        },
    }

    return AnalysisPackage(
        symbol="FPT",
        company={"name": "FPT Corporation", "sector": "Technology"},
        price_summary={"close": 123.45, "change_pct": 1.2, "volume": 1000000},
        financial_summary=financial_summary,
        news_summary=news_summary,
        signals={"trend": "positive"},
        risks={"event_risk": "medium"},
        breadth_context=breadth_context,
        data_quality={
            "provider_health": {"status": provider_health_status},
            "sections": section_statuses,
        },
        missing_sections=missing,
        provider_metadata={"provider_name": "free_provider"},
        generated_at=generated_at or datetime(2026, 3, 23, 12, 0, 0),
    )


def test_build_data_quality_summary_returns_expected_keys(base_analysis_package: AnalysisPackage) -> None:
    summary = build_data_quality_summary(base_analysis_package)

    assert set(summary.keys()) == {
        "symbol",
        "provider_name",
        "generated_at",
        "missing_sections",
        "overall_status",
        "section_statuses",
    }
    assert summary["symbol"] == "FPT"
    assert summary["provider_name"] == "free_provider"
    assert summary["generated_at"] == "2026-03-23T12:00:00"


def test_build_data_quality_summary_sets_high_when_no_optional_sections_missing() -> None:
    package = make_analysis_package(missing_sections=[])

    summary = build_data_quality_summary(package)

    assert summary["overall_status"] == "high"


def test_build_data_quality_summary_sets_medium_when_one_or_two_sections_missing() -> None:
    package_one_missing = make_analysis_package(missing_sections=["financial_summary"])
    package_two_missing = make_analysis_package(missing_sections=["financial_summary", "news_summary"])

    summary_one_missing = build_data_quality_summary(package_one_missing)
    summary_two_missing = build_data_quality_summary(package_two_missing)

    assert summary_one_missing["overall_status"] == "medium"
    assert summary_two_missing["overall_status"] == "medium"


def test_build_data_quality_summary_sets_low_when_many_sections_missing_or_provider_health_has_error() -> None:
    package_many_missing = make_analysis_package(
        missing_sections=["financial_summary", "news_summary", "breadth_context"],
    )
    package_provider_error = make_analysis_package(
        missing_sections=[],
        provider_health_status="error",
    )

    summary_many_missing = build_data_quality_summary(package_many_missing)
    summary_provider_error = build_data_quality_summary(package_provider_error)

    assert summary_many_missing["overall_status"] == "low"
    assert summary_provider_error["overall_status"] == "low"


def test_ensure_data_quality_section_appends_section_when_missing(
    base_analysis_package: AnalysisPackage,
) -> None:
    markdown = "# Trade Plan: FPT\n\n## Summary\n- Sample content\n"

    result = ensure_data_quality_section(markdown, base_analysis_package)

    assert "## Data coverage / Data quality" in result
    assert "- provider: `free_provider`" in result
    assert "- overall_status: `high`" in result


def test_ensure_data_quality_section_does_not_append_duplicate_section(
    base_analysis_package: AnalysisPackage,
) -> None:
    markdown = (
        "# Trade Plan: FPT\n\n"
        "## Data coverage / Data quality\n"
        "- provider: `free_provider`\n"
        "- overall_status: `high`\n"
    )

    result = ensure_data_quality_section(markdown, base_analysis_package)

    assert result.count("## Data coverage / Data quality") == 1


def test_export_markdown_report_creates_markdown_file_successfully(
    base_analysis_package: AnalysisPackage,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "trade_plan_fpt.md"
    markdown = "# Trade Plan: FPT\n\n## Summary\n- Export test\n"

    result = export_markdown_report(
        analysis_package=base_analysis_package,
        markdown_text=markdown,
        output_path=str(output_path),
    )

    assert output_path.exists()
    saved_content = output_path.read_text(encoding="utf-8")
    assert "## Data coverage / Data quality" in saved_content
    assert result.output_path == str(output_path)


def test_export_markdown_report_returns_expected_tracking_fields(tmp_path: Path) -> None:
    package = make_analysis_package(missing_sections=["financial_summary", "news_summary"])
    output_path = tmp_path / "trade_plan_fpt.md"
    markdown = "# Trade Plan: FPT\n\n## Summary\n- Tracking test\n"

    result = export_markdown_report(
        analysis_package=package,
        markdown_text=markdown,
        output_path=str(output_path),
    )

    assert result.files_created == [str(output_path)]
    assert result.errors == []
    assert result.warnings == ["Missing optional sections: `financial_summary`, `news_summary`"]
    assert result.data_quality_summary["symbol"] == "FPT"
    assert result.data_quality_summary["provider_name"] == "free_provider"
    assert result.data_quality_summary["overall_status"] == "medium"
