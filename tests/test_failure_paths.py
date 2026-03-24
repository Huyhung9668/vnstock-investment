from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import daily_run
import run_trade_plan_v2


def make_workspace_dir(name: str) -> Path:
    base_dir = PROJECT_ROOT / "test_artifacts"
    target = base_dir / f"{name}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_generate_trade_plan_raises_explicit_error_when_source_returns_empty_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_trade_plan_v2, "create_provider", lambda: object())

    def fake_build_analysis_package(provider: object, symbol: str) -> object:
        raise ValueError("No price history returned for FPT")

    monkeypatch.setattr(run_trade_plan_v2, "build_analysis_package", fake_build_analysis_package)

    with pytest.raises(ValueError, match="No price history returned for FPT"):
        run_trade_plan_v2.generate_trade_plan("FPT")


def test_generate_trade_plan_raises_explicit_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_trade_plan_v2, "create_provider", lambda: object())

    def fake_build_analysis_package(provider: object, symbol: str) -> object:
        raise TimeoutError("Source timeout while fetching data for FPT")

    monkeypatch.setattr(run_trade_plan_v2, "build_analysis_package", fake_build_analysis_package)

    with pytest.raises(TimeoutError, match="Source timeout while fetching data for FPT"):
        run_trade_plan_v2.generate_trade_plan("FPT")


def test_daily_run_continues_after_one_symbol_failure_and_keeps_summary_counts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace_dir = make_workspace_dir("failure_paths_counts")
    reports_dir = workspace_dir / "reports"
    manifests_dir = reports_dir / "manifests"
    calls: list[tuple[str, str]] = []

    def fake_load_yaml(path: Path) -> dict[str, object]:
        if path.name == "watchlist.yaml":
            return {"symbols": ["FPT", "MWG", "HPG"]}
        if path.name == "runtime.yaml":
            return {
                "mode": "paid_with_free_fallback",
                "output": {
                    "reports_dir": str(reports_dir.relative_to(PROJECT_ROOT)),
                    "manifests_dir": str(manifests_dir.relative_to(PROJECT_ROOT)),
                },
                "features": {"export_html": False},
                "allowed_modes": ["free", "paid", "paid_with_free_fallback"],
            }
        if path.name == "sources.yaml":
            return {"primary": "paid", "fallback_order": ["free"]}
        raise AssertionError(f"Unexpected config path: {path}")

    def fake_process_symbol(**kwargs: object) -> daily_run.SymbolRunResult:
        symbol = str(kwargs["symbol"])
        provider_sequence = list(kwargs["provider_sequence"])
        calls.append((symbol, provider_sequence[0]))

        if symbol == "MWG":
            return daily_run.SymbolRunResult(
                symbol=symbol,
                status="failed",
                source_used="free_provider",
                fallback_used=True,
                degraded_mode=False,
                warnings=["paid failed for MWG: RuntimeError: provider failed"],
                errors=["paid failed for MWG: RuntimeError: provider failed"],
                files_created=[],
            )

        return daily_run.SymbolRunResult(
            symbol=symbol,
            status="success",
            source_used="free_provider",
            fallback_used=symbol == "FPT",
            degraded_mode=False,
            warnings=[],
            errors=[],
            files_created=[f"reports/trade_plan_{symbol.lower()}.md"],
        )

    monkeypatch.setattr(daily_run, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(daily_run, "process_symbol", fake_process_symbol)
    monkeypatch.setattr(daily_run, "notify_telegram", lambda summary: None)
    monkeypatch.setattr(
        daily_run,
        "parse_args",
        lambda: type("Args", (), {"config_dir": str(PROJECT_ROOT / "config")})(),
    )

    try:
        exit_code = daily_run.main()
        output = capsys.readouterr().out
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

    assert exit_code == 1
    assert calls == [("FPT", "paid"), ("MWG", "paid"), ("HPG", "paid")]
    assert "'success': 2" in output
    assert "'failed': 1" in output
    assert "'warnings': 1" in output


def test_daily_run_still_creates_manifest_when_partial_optional_source_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_dir = make_workspace_dir("failure_paths_manifest")
    reports_dir = workspace_dir / "reports"
    manifests_dir = reports_dir / "manifests"

    def fake_load_yaml(path: Path) -> dict[str, object]:
        if path.name == "watchlist.yaml":
            return {"symbols": ["FPT"]}
        if path.name == "runtime.yaml":
            return {
                "mode": "free",
                "output": {
                    "reports_dir": str(reports_dir.relative_to(PROJECT_ROOT)),
                    "manifests_dir": str(manifests_dir.relative_to(PROJECT_ROOT)),
                },
                "features": {"export_html": False},
                "allowed_modes": ["free"],
            }
        if path.name == "sources.yaml":
            return {"primary": "free", "fallback_order": ["free"]}
        raise AssertionError(f"Unexpected config path: {path}")

    def fake_process_symbol(**kwargs: object) -> daily_run.SymbolRunResult:
        manifest_path = manifests_dir / "manifest_fpt_demo.json"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "run_id": "demo",
                    "run_date": "2026-03-23T15:00:00+07:00",
                    "symbols": ["FPT"],
                    "mode": "free",
                    "source_used": "free_provider",
                    "files_created": ["reports/trade_plan_fpt.md"],
                    "warnings": ["News summary error; continuing with degraded output."],
                    "errors": [],
                    "duration_seconds": 1.0,
                    "data_quality_summary": {"degraded_mode": True},
                }
            ),
            encoding="utf-8",
        )

        return daily_run.SymbolRunResult(
            symbol="FPT",
            status="success",
            source_used="free_provider",
            fallback_used=False,
            degraded_mode=True,
            warnings=["News summary error; continuing with degraded output."],
            errors=[],
            files_created=["reports/trade_plan_fpt.md", str(manifest_path)],
            manifest_path=str(manifest_path),
            degraded_reasons=["warning: News summary error; continuing with degraded output."],
        )

    monkeypatch.setattr(daily_run, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(daily_run, "process_symbol", fake_process_symbol)
    monkeypatch.setattr(daily_run, "notify_telegram", lambda summary: None)
    monkeypatch.setattr(
        daily_run,
        "parse_args",
        lambda: type("Args", (), {"config_dir": str(PROJECT_ROOT / "config")})(),
    )

    try:
        exit_code = daily_run.main()
    finally:
        manifest_file = manifests_dir / "manifest_fpt_demo.json"
        assert manifest_file.exists()
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert payload["data_quality_summary"]["degraded_mode"] is True
        shutil.rmtree(workspace_dir, ignore_errors=True)

    assert exit_code == 0


def test_notifier_skip_is_safe_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with caplog.at_level("WARNING"):
        daily_run.notify_telegram(
            {
                "total": 1,
                "success": 1,
                "failed": 0,
                "warnings": 0,
                "duration": 1.0,
                "source_used": ["free_provider"],
                "fallback_used": False,
                "files_created": [],
            }
        )

    assert "Telegram notifier skipped: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID." in caplog.text
