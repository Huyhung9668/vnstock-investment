from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TYPE_CHECKING


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.analysis_builder import build_analysis_package
from services.trade_plan_service import render_trade_plan

if TYPE_CHECKING:
    from providers.base import TradePlanningProvider


REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(slots=True)
class TradePlanRunResult:
    symbol: str
    markdown: str
    output_path: str
    files_created: list[str]
    warnings: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the trade planning pipeline and export a markdown report.",
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
    return parser.parse_args()


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must be a non-empty string")
    return normalized


def build_report_path(symbol: str) -> Path:
    return REPORTS_DIR / f"trade_plan_{symbol.lower()}.md"


def ensure_reports_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def create_provider() -> "TradePlanningProvider":
    try:
        from providers.free_provider import FreeTradePlanningProvider
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Khong tim thay `providers.free_provider.FreeTradePlanningProvider`. "
            "Hay kiem tra file `providers/free_provider.py` va class `FreeTradePlanningProvider`."
        ) from exc

    return FreeTradePlanningProvider()


def generate_trade_plan(symbol: str) -> TradePlanRunResult:
    normalized_symbol = normalize_symbol(symbol)
    provider = create_provider()
    analysis_package = build_analysis_package(provider, normalized_symbol)
    markdown = render_trade_plan(analysis_package)

    ensure_reports_dir(REPORTS_DIR)
    output_path = build_report_path(normalized_symbol)
    output_path.write_text(markdown, encoding="utf-8")

    return TradePlanRunResult(
        symbol=normalized_symbol,
        markdown=markdown,
        output_path=str(output_path),
        files_created=[str(output_path)],
        warnings=[],
    )


def run(symbol: str) -> str:
    result = generate_trade_plan(symbol)
    return result.markdown


def main() -> int:
    args = parse_args()
    symbol = args.symbol_flag or args.symbol
    if not symbol:
        raise ValueError("symbol is required. Use `python scripts/run_trade_plan_v2.py FPT` or `--symbol FPT`.")

    result = generate_trade_plan(symbol)
    print(result.markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
