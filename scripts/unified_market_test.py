from pathlib import Path
import sys

import pandas as pd


def save_output(df: pd.DataFrame, symbol: str) -> Path:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{symbol.lower()}_unified_market.csv"
    df.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    symbol = "VCB"

    try:
        from vnstock_data import Stock
    except ImportError:
        print("vnstock_data is not installed.")
        print("Run: python -m pip install vnstock_data")
        sys.exit(1)

    try:
        stock = Stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start="2024-01-01", end="2024-12-31")

        if df is None or df.empty:
            raise ValueError(f"No data returned for {symbol}")

        output_path = save_output(df, symbol)

        print(f"Unified market test completed for {symbol}")
        print(f"Rows saved : {len(df)}")
        print(f"Output file: {output_path}")
        print(df.head())
    except Exception as exc:
        print(f"Unified market test failed: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()