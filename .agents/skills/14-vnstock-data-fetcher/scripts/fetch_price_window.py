from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load a local CSV price window for a symbol.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--input", required=True, help="Path to CSV file")
    parser.add_argument("--rows", type=int, default=20, help="Rows to keep from the tail")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.input)
    df = pd.read_csv(path)
    df.columns = [str(col).strip().lower() for col in df.columns]
    result = df.tail(max(args.rows, 1)).copy()
    result["symbol"] = args.symbol.strip().upper()
    print(result.to_json(orient="records", force_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
