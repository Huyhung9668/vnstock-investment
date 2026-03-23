from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.market_overview_service import build_market_overview

INPUT_PATH = PROJECT_ROOT / "data" / "derived" / "universe_scores.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "derived" / "market_overview.json"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    market_overview = build_market_overview(df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(market_overview, file, ensure_ascii=False, indent=2)

    print(f"Saved market overview -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
