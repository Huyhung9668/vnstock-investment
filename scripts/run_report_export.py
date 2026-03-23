from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.analysis_builder import build_analysis_package
from services.manifest_service import create_manifest, save_manifest
from services.report_exporter import export_markdown_report
from services.trade_plan_service import render_trade_plan

if TYPE_CHECKING:
    from providers.base import TradePlanningProvider


REPORTS_DIR = PROJECT_ROOT / "reports"
MANIFESTS_DIR = REPORTS_DIR / "manifests"
DEFAULT_MODE = "free"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run trade plan export and write both markdown report and manifest JSON.",
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        type=str,
        help="Stock symbol to analyze.",
    )
    parser.add_argument(
        "--symbol",
        dest="symbol_flag",
        type=str,
        help="Stock symbol to analyze.",
    )
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        type=str,
        help="Execution mode recorded in manifest. Default: free",
    )
    return parser.parse_args()


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must be a non-empty string")
    return normalized


def create_provider() -> "TradePlanningProvider":
    from providers.free_provider import FreeTradePlanningProvider

    return FreeTradePlanningProvider()


def build_report_output_path(symbol: str) -> Path:
    return REPORTS_DIR / f"trade_plan_{symbol.lower()}.md"


def build_manifest_output_path(run_id: str, symbol: str) -> Path:
    return MANIFESTS_DIR / f"manifest_{symbol.lower()}_{run_id}.json"


def ensure_output_directories() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)


def run(symbol: str, *, mode: str) -> tuple[str, str]:
    started_at = time.perf_counter()
    normalized_symbol = normalize_symbol(symbol)

    ensure_output_directories()

    provider = create_provider()
    analysis_package = build_analysis_package(provider, normalized_symbol)
    markdown_text = render_trade_plan(analysis_package)

    report_result = export_markdown_report(
        analysis_package=analysis_package,
        markdown_text=markdown_text,
        output_path=str(build_report_output_path(normalized_symbol)),
    )

    duration_seconds = time.perf_counter() - started_at
    provider_name = str(provider.provider_name())

    manifest = create_manifest(
        symbols=[normalized_symbol],
        mode=mode,
        source_used=provider_name,
        files_created=list(report_result.files_created),
        warnings=list(report_result.warnings),
        errors=list(report_result.errors),
        duration_seconds=duration_seconds,
        data_quality_summary=dict(report_result.data_quality_summary),
    )

    manifest_path = build_manifest_output_path(manifest.run_id, normalized_symbol)
    saved_manifest_path = save_manifest(manifest, str(manifest_path))

    manifest.files_created.append(saved_manifest_path)
    saved_manifest_path = save_manifest(manifest, str(manifest_path))

    return report_result.output_path, saved_manifest_path


def main() -> int:
    args = parse_args()
    symbol = args.symbol_flag or args.symbol
    if not symbol:
        raise ValueError("symbol is required. Use `python scripts/run_report_export.py FPT` or `--symbol FPT`.")

    report_path, manifest_path = run(symbol, mode=args.mode)
    print(f"Report path: {report_path}")
    print(f"Manifest path: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
