from pathlib import Path

import pandas as pd
from vnstock import Listing


OUTPUT_PATH = Path("data/raw/universe.csv")


def build_universe() -> None:
    listing = Listing()
    listing_df = listing.symbols_by_exchange()

    if not isinstance(listing_df, pd.DataFrame):
        raise TypeError("Listing.symbols_by_exchange() must return a pandas DataFrame")
    if "symbol" not in listing_df.columns:
        raise ValueError("Listing.symbols_by_exchange() did not return a 'symbol' column")

    df = (
        listing_df.loc[:, ["symbol"]]
        .dropna(subset=["symbol"])
        .assign(symbol=lambda frame: frame["symbol"].astype(str).str.strip().str.upper())
    )
    df = df[df["symbol"] != ""].drop_duplicates(subset=["symbol"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved universe: {len(df)} symbols -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build_universe()
