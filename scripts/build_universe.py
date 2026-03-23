from __future__ import annotations

from pathlib import Path

import pandas as pd

OUTPUT_PATH = Path("data/raw/universe.csv")
DEFAULT_SOURCE = "kbs"


def log(message: str) -> None:
    print(f"[build_universe] {message}")


def fetch_universe(source: str = DEFAULT_SOURCE) -> pd.DataFrame:
    from vnstock import Listing

    log(f"Fetching base symbol list from vnstock (source={source})")
    listing = Listing(source=source, show_log=False)
    df = listing.all_symbols()
    if df is None or df.empty:
        raise RuntimeError("vnstock returned an empty universe DataFrame.")
    return df


def normalize_universe(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df.columns = [str(column).strip().lower() for column in clean_df.columns]
    clean_df = clean_df.dropna(how="all")

    if "symbol" in clean_df.columns:
        clean_df["symbol"] = clean_df["symbol"].astype(str).str.strip().str.upper()
        clean_df = clean_df[clean_df["symbol"] != ""]

    clean_df = clean_df.drop_duplicates().reset_index(drop=True)

    priority_columns = ["symbol", "organ_name", "exchange", "industry_name"]
    ordered_columns = [column for column in priority_columns if column in clean_df.columns]
    ordered_columns.extend(column for column in clean_df.columns if column not in ordered_columns)
    clean_df = clean_df.loc[:, ordered_columns]

    return clean_df


def save_universe(df: pd.DataFrame) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    return OUTPUT_PATH


def print_summary(df: pd.DataFrame, output_path: Path) -> None:
    log("Universe build completed.")
    log(f"Rows saved: {len(df)}")
    log(f"Columns: {', '.join(df.columns)}")
    log(f"Output: {output_path}")

    preview_columns = [column for column in ["symbol", "organ_name", "exchange"] if column in df.columns]
    if preview_columns:
        log("Preview:")
        print(df.loc[:, preview_columns].head(5).to_string(index=False))


def main() -> int:
    df = fetch_universe()
    log(f"Received {len(df)} rows from vnstock")
    output_path = save_universe(df)
    print_summary(df, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
