from pathlib import Path
import traceback

import pandas as pd
from vnstock import Vnstock


def fetch_stock_data(symbol: str) -> pd.DataFrame:
    try:
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start="2024-01-01", end="2024-12-31")

        if df is None or df.empty:
            raise ValueError(f"No data returned for symbol: {symbol}")

        return df
    except Exception as exc:
        print("fetch_stock_data failed")
        print(f"symbol: {symbol}")
        print(f"error type: {type(exc).__name__}")
        print(f"error: {exc}")
        traceback.print_exc()
        raise


def save_data(df: pd.DataFrame, symbol: str) -> Path:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{symbol}_price.csv"
    df.to_csv(file_path, index=False)
    return file_path


def main() -> None:
    symbol = "VCB"
    df = fetch_stock_data(symbol)
    file_path = save_data(df, symbol)

    print(f"Saved: {file_path}")
    print(df.head())


if __name__ == "__main__":
    main()