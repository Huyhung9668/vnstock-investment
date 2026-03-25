from __future__ import annotations

import json
import logging
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
from models.analysis_package import AnalysisPackage
from providers.base import TradePlanningProvider


def make_workspace_dir(name: str) -> Path:
    base_dir = PROJECT_ROOT / "test_artifacts"
    target = base_dir / f"{name}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=True)
    return target


class FakeProvider(TradePlanningProvider):
    def __init__(self, name: str) -> None:
        self._name = name

    def provider_name(self) -> str:
        return self._name

    def health_check(self) -> dict[str, object]:
        return {"status": "ok"}

    def get_company_profile(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "name": f"{symbol} Corp"}

    def get_price_summary(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "last_close": 100.0}

    def get_financial_summary(self, symbol: str) -> dict[str, object] | None:
        return {"status": "available"}

    def get_news_summary(self, symbol: str) -> dict[str, object] | None:
        return {"status": "available"}

    def get_breadth_context(self) -> dict[str, object] | None:
        return {"status": "available"}


def make_analysis_package(
    *,
    symbol: str,
    provider_name: str = "free_provider",
    financial_status: str = "ok",
    news_status: str = "ok",
    breadth_status: str = "missing",
) -> AnalysisPackage:
    financial_summary = {"status": "available"} if financial_status == "ok" else None
    news_summary = {"status": "available"} if news_status == "ok" else None
    breadth_context = {"status": "available"} if breadth_status == "ok" else None

    return AnalysisPackage(
        symbol=symbol,
        company={"name": f"{symbol} Corporation"},
        price_summary={"last_close": 100.0, "day_change_pct": 1.2},
        financial_summary=financial_summary,
        news_summary=news_summary,
        signals={},
        risks={},
        breadth_context=breadth_context,
        data_quality={
            "provider_health": {"status": "ok"},
            "sections": {
                "company": {"status": "ok", "present": True},
                "price_summary": {"status": "ok", "present": True},
                "financial_summary": {"status": financial_status, "present": financial_status == "ok"},
                "news_summary": {"status": news_status, "present": news_status == "ok"},
                "breadth_context": {"status": breadth_status, "present": breadth_status == "ok"},
            },
        },
        missing_sections=[
            section
            for section, status in (
                ("financial_summary", financial_status),
                ("news_summary", news_status),
                ("breadth_context", breadth_status),
            )
            if status != "ok"
        ],
        provider_metadata={"provider_name": provider_name},
    )


def test_build_analysis_warnings_does_not_degrade_when_only_breadth_is_missing() -> None:
    analysis_package = make_analysis_package(
        symbol="FPT",
        financial_status="ok",
        news_status="ok",
        breadth_status="missing",
    )

    warnings, degraded_mode = daily_run._build_analysis_warnings(analysis_package)

    assert degraded_mode is False
    assert "breadth_context missing; continuing with reduced context" in warnings


def test_rank_candidates_synthesizes_market_overview_from_ranking(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_bundle = daily_run.RuntimeConfigBundle(
        config_dir=PROJECT_ROOT / "config",
        runtime={
            "mode": "free",
            "selection": {"mode": "top_from_universe", "top_n": 5},
            "output": {"report_dir": "reports", "manifest_dir": "manifests"},
            "features": {"market_overview": False},
        },
        sources={
            "providers": {"primary": "free", "fallback": "free"},
            "services": {"market": "free", "news": "free", "financials": "free"},
        },
        watchlist={"symbols": []},
        universe={},
    )
    context = daily_run.build_run_context(runtime_bundle)

    ranking_df = daily_run._normalize_ranking_dataframe(
        daily_run.pd.DataFrame(
            [
                {"symbol": "FPT", "score": 0.92, "return_3m": 0.15, "avg_volume": 1_000_000, "sector": "TECH"},
                {"symbol": "MWG", "score": 0.81, "return_3m": 0.09, "avg_volume": 900_000, "sector": "RETAIL"},
                {"symbol": "VCB", "score": 0.65, "return_3m": -0.02, "avg_volume": 800_000, "sector": "BANK"},
            ]
        )
    )

    monkeypatch.setattr(daily_run, "_load_dataframe", lambda path: ranking_df.copy())

    daily_run.rank_candidates(runtime_bundle, context)

    assert context.total_ranked == 3
    assert context.market_overview is not None
    assert context.market_overview_path == "in_memory:ranking_table_fallback"
    assert context.market_overview["source"] == "ranking_table_fallback"
    assert context.market_overview["breadth"]["total_symbols"] == 3


def test_load_config_successfully_and_run_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace_dir = make_workspace_dir("daily_run_load_config")
    config_dir = workspace_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    (config_dir / "watchlist.yaml").write_text("symbols:\n  - FPT\n  - MWG\n", encoding="utf-8")
    (config_dir / "runtime.yaml").write_text(
        "mode: free\noutput:\n  reports_dir: reports\n  manifests_dir: reports/manifests\nfeatures:\n  export_html: false\nallowed_modes:\n  - free\n",
        encoding="utf-8",
    )
    (config_dir / "sources.yaml").write_text("primary: free\nfallback_order:\n  - free\n", encoding="utf-8")

    monkeypatch.setattr(
        daily_run,
        "parse_args",
        lambda: type("Args", (), {"config_dir": str(config_dir)})(),
    )
    monkeypatch.setattr(
        daily_run,
        "process_symbol",
        lambda **kwargs: daily_run.SymbolRunResult(
            symbol=str(kwargs["symbol"]),
            status="success",
            source_used="free_provider",
            fallback_used=False,
            degraded_mode=False,
            warnings=[],
            errors=[],
            files_created=[],
        ),
    )
    monkeypatch.setattr(daily_run, "notify_telegram", lambda summary: None)

    try:
        exit_code = daily_run.main()
        output = capsys.readouterr().out
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

    assert exit_code == 0
    assert "'total': 2" in output
    assert "'success': 2" in output
    assert "'failed': 0" in output


def test_fallback_from_paid_to_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_symbol_pipeline(**kwargs: object) -> daily_run.SymbolRunResult:
        provider_name = str(kwargs["provider_name"])
        calls.append(provider_name)
        if provider_name == "paid":
            raise RuntimeError("paid provider unavailable")
        return daily_run.SymbolRunResult(
            symbol="FPT",
            status="success",
            source_used="free_provider",
            fallback_used=False,
            degraded_mode=False,
            warnings=[],
            errors=[],
            files_created=["reports/trade_plan_fpt.md"],
        )

    monkeypatch.setattr(daily_run, "run_symbol_pipeline", fake_run_symbol_pipeline)

    result = daily_run.process_symbol(
        symbol="FPT",
        provider_sequence=["paid", "free"],
        mode="paid_with_free_fallback",
        sources_config={},
        reports_dir=PROJECT_ROOT / "reports",
        manifests_dir=PROJECT_ROOT / "reports" / "manifests",
        export_html=False,
    )

    assert calls == ["paid", "free"]
    assert result.status == "success"
    assert result.fallback_used is True
    assert result.source_used == "free_provider"
    assert any("Fallback provider used for FPT: free" == warning for warning in result.warnings)


def test_run_symbol_pipeline_still_creates_manifest_when_optional_source_partially_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_dir = make_workspace_dir("daily_run_manifest_partial")
    reports_dir = workspace_dir / "reports"
    manifests_dir = reports_dir / "manifests"

    fake_provider = FakeProvider("free_provider")
    analysis_package = make_analysis_package(
        symbol="FPT",
        financial_status="ok",
        news_status="error",
        breadth_status="missing",
    )

    monkeypatch.setattr(daily_run, "create_provider", lambda **kwargs: fake_provider)
    monkeypatch.setattr(daily_run, "build_analysis_package", lambda provider, symbol: analysis_package)
    monkeypatch.setattr(daily_run, "render_trade_plan", lambda package: "# Trade Plan: FPT\n")

    try:
        result = daily_run.run_symbol_pipeline(
            symbol="FPT",
            provider_name="free",
            mode="free",
            sources_config={},
            reports_dir=reports_dir,
            manifests_dir=manifests_dir,
            export_html=False,
        )

        assert result.status == "success"
        assert result.degraded_mode is False
        assert result.manifest_path is not None
        assert Path(result.manifest_path).exists()

        manifest_payload = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest_payload["symbols"] == ["FPT"]
        assert manifest_payload["source_used"] == "free_provider"
        assert manifest_payload["data_quality_summary"]["degraded_mode"] is False
        assert any("breadth_context" in warning for warning in manifest_payload["warnings"])
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


def test_notifier_skip_is_safe_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with caplog.at_level(logging.WARNING):
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
