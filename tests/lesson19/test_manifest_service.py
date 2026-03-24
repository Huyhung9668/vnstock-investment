from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from models.report_manifest import ReportManifest
from services.manifest_service import create_manifest, save_manifest


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def make_manifest() -> ReportManifest:
    return create_manifest(
        symbols=["fpt", "vcb"],
        mode="daily",
        source_used="free_provider",
        files_created=["reports/trade_plan_fpt.md"],
        warnings=["missing news_summary"],
        errors=[],
        duration_seconds=3.5,
        data_quality_summary={"overall_status": "medium"},
    )


def test_create_manifest_returns_valid_report_manifest() -> None:
    manifest = make_manifest()

    assert isinstance(manifest, ReportManifest)
    manifest.validate()
    assert manifest.mode == "daily"
    assert manifest.source_used == "free_provider"
    assert manifest.files_created == ["reports/trade_plan_fpt.md"]
    assert manifest.warnings == ["missing news_summary"]
    assert manifest.errors == []
    assert manifest.duration_seconds == 3.5
    assert manifest.data_quality_summary == {"overall_status": "medium"}


def test_create_manifest_generates_run_id() -> None:
    manifest = make_manifest()

    assert isinstance(manifest.run_id, str)
    assert manifest.run_id.strip() != ""


def test_create_manifest_sets_valid_run_date() -> None:
    before = datetime.now(VIETNAM_TZ)
    manifest = make_manifest()
    after = datetime.now(VIETNAM_TZ)

    assert isinstance(manifest.run_date, datetime)
    assert before <= manifest.run_date <= after


def test_save_manifest_creates_json_file_successfully(tmp_path: Path) -> None:
    manifest = make_manifest()
    output_path = tmp_path / "manifest.json"

    saved_path = save_manifest(manifest, str(output_path))

    assert saved_path == str(output_path)
    assert output_path.exists()


def test_save_manifest_creates_parent_directory_if_needed(tmp_path: Path) -> None:
    manifest = make_manifest()
    output_path = tmp_path / "nested" / "logs" / "manifest.json"

    save_manifest(manifest, str(output_path))

    assert output_path.parent.exists()
    assert output_path.exists()


def test_save_manifest_persists_serialized_json_data_correctly(tmp_path: Path) -> None:
    manifest = make_manifest()
    output_path = tmp_path / "manifest.json"

    save_manifest(manifest, str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == manifest.to_dict()
    assert payload["run_date"] == manifest.run_date.isoformat()


def test_create_manifest_normalizes_symbols_when_manifest_model_applies_normalization() -> None:
    manifest = make_manifest()

    assert manifest.symbols == ["FPT", "VCB"]


def test_save_manifest_raises_for_empty_output_path() -> None:
    manifest = make_manifest()

    try:
        save_manifest(manifest, "")
    except ValueError as exc:
        assert str(exc) == "output_path must be a non-empty string"
    else:
        raise AssertionError("Expected ValueError for empty output path")


def test_save_manifest_raises_for_directory_output_path(tmp_path: Path) -> None:
    manifest = make_manifest()

    try:
        save_manifest(manifest, str(tmp_path))
    except IsADirectoryError as exc:
        assert "output_path must be a file path" in str(exc)
    else:
        raise AssertionError("Expected IsADirectoryError for directory output path")
