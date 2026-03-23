from __future__ import annotations

from datetime import datetime

import pytest

from models.report_manifest import ReportManifest


def make_manifest() -> ReportManifest:
    return ReportManifest(
        run_id="run-123",
        run_date=datetime(2026, 3, 23, 12, 0, 0),
        symbols=["fpt", "vcb"],
        mode="daily",
        source_used="free_provider",
        files_created=["reports/trade_plan_fpt.md"],
        warnings=["missing news_summary"],
        errors=[],
        duration_seconds=2.5,
        data_quality_summary={"overall_status": "medium"},
    )


def test_to_dict_serializes_run_date_as_iso_string() -> None:
    manifest = make_manifest()

    payload = manifest.to_dict()

    assert payload["run_date"] == "2026-03-23T12:00:00"


def test_from_dict_deserializes_into_report_manifest() -> None:
    payload = {
        "run_id": "run-123",
        "run_date": "2026-03-23T12:00:00",
        "symbols": ["fpt", "vcb"],
        "mode": "daily",
        "source_used": "free_provider",
        "files_created": ["reports/trade_plan_fpt.md"],
        "warnings": ["missing news_summary"],
        "errors": [],
        "duration_seconds": 2.5,
        "data_quality_summary": {"overall_status": "medium"},
    }

    manifest = ReportManifest.from_dict(payload)

    assert isinstance(manifest, ReportManifest)
    assert manifest.run_id == "run-123"
    assert manifest.run_date == datetime(2026, 3, 23, 12, 0, 0)
    assert manifest.symbols == ["FPT", "VCB"]
    assert manifest.mode == "daily"
    assert manifest.source_used == "free_provider"


def test_validate_raises_for_empty_run_id() -> None:
    with pytest.raises(ValueError, match="run_id must be a non-empty string"):
        ReportManifest(
            run_id="",
            run_date=datetime(2026, 3, 23, 12, 0, 0),
            symbols=["FPT"],
            mode="daily",
            source_used="free_provider",
            files_created=[],
            warnings=[],
            errors=[],
            duration_seconds=1.0,
            data_quality_summary={},
        )


def test_validate_raises_for_symbols_not_list_of_strings() -> None:
    with pytest.raises(TypeError, match="symbols must be a list\\[str\\]"):
        ReportManifest(
            run_id="run-123",
            run_date=datetime(2026, 3, 23, 12, 0, 0),
            symbols=["FPT", 123],  # type: ignore[list-item]
            mode="daily",
            source_used="free_provider",
            files_created=[],
            warnings=[],
            errors=[],
            duration_seconds=1.0,
            data_quality_summary={},
        )


def test_validate_raises_for_negative_duration_seconds() -> None:
    with pytest.raises(ValueError, match="duration_seconds must be greater than or equal to 0"):
        ReportManifest(
            run_id="run-123",
            run_date=datetime(2026, 3, 23, 12, 0, 0),
            symbols=["FPT"],
            mode="daily",
            source_used="free_provider",
            files_created=[],
            warnings=[],
            errors=[],
            duration_seconds=-1.0,
            data_quality_summary={},
        )


def test_validate_raises_for_data_quality_summary_not_dict() -> None:
    with pytest.raises(TypeError, match="data_quality_summary must be a dictionary"):
        ReportManifest(
            run_id="run-123",
            run_date=datetime(2026, 3, 23, 12, 0, 0),
            symbols=["FPT"],
            mode="daily",
            source_used="free_provider",
            files_created=[],
            warnings=[],
            errors=[],
            duration_seconds=1.0,
            data_quality_summary=[],  # type: ignore[arg-type]
        )


def test_symbols_are_normalized_to_uppercase_when_supported() -> None:
    manifest = make_manifest()

    assert manifest.symbols == ["FPT", "VCB"]
