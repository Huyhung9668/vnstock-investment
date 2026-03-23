from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from vnstock import stock
except ImportError:
    from vnstock import Listing, Quote

    class _StockCompat:
        class listing:
            @staticmethod
            def symbols_by_exchange() -> pd.DataFrame:
                return Listing().symbols_by_exchange()

        class quote:
            @staticmethod
            def history(
                *,
                symbol: str,
                period: str = "1y",
                interval: str = "1d",
                start: str | None = None,
                end: str | None = None,
            ) -> pd.DataFrame:
                _ = period
                return Quote(symbol=symbol).history(
                    start=start,
                    end=end,
                    interval=interval.upper(),
                )

    stock = _StockCompat()

from services.news_aggregation_service import aggregate_news
from services.news_scoring_service import merge_news_scores_into_universe
from services.ranking_service import rank_universe_from_csv


CONFIG_PATH = Path("config/universe.yaml")
UNIVERSE_PATH = Path("data/raw/universe.csv")
OUTPUT_DIR = Path("data/derived")
RAW_SCAN_OUTPUT = OUTPUT_DIR / "universe_scan_raw.csv"
RANKED_OUTPUT = OUTPUT_DIR / "universe_scores.csv"
TOP10_OUTPUT = OUTPUT_DIR / "top10_symbols.json"
MARKET_NEWS_OUTPUT = OUTPUT_DIR / "market_news_summary.json"

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def fetch_symbol_news_rows(symbol: str) -> list[dict[str, Any]]:
    _ = symbol
    return []


def fetch_market_news_rows() -> list[dict[str, Any]]:
    return []


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_universe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Universe file not found: {path}")

    df = pd.read_csv(path)
    df.columns = [str(column).strip().lower() for column in df.columns]

    if "symbol" not in df.columns:
        raise ValueError("Universe file must contain a `symbol` column.")

    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

    if "exchange" not in df.columns:
        df["exchange"] = "UNKNOWN"

    if "sector" not in df.columns:
        df["sector"] = "UNKNOWN"

    return df.drop_duplicates(subset=["symbol"]).reset_index(drop=True)


def build_exchange_mapping() -> dict[str, str]:
    try:
        listing_data = stock.listing.symbols_by_exchange()
    except Exception as exc:
        LOGGER.warning("Could not build exchange mapping from vnstock: %s", exc)
        return {}

    mapping: dict[str, str] = {}

    if isinstance(listing_data, dict):
        for exchange, symbols in listing_data.items():
            if isinstance(symbols, (list, tuple, set)):
                for symbol in symbols:
                    mapping[str(symbol).strip().upper()] = str(exchange).strip().upper()
            elif isinstance(symbols, pd.DataFrame):
                symbol_column = next(
                    (col for col in symbols.columns if str(col).strip().lower() == "symbol"),
                    None,
                )
                if symbol_column is not None:
                    for symbol in symbols[symbol_column].dropna().astype(str):
                        mapping[symbol.strip().upper()] = str(exchange).strip().upper()
    elif isinstance(listing_data, pd.DataFrame):
        normalized_columns = {str(col).strip().lower(): col for col in listing_data.columns}
        symbol_col = normalized_columns.get("symbol")
        exchange_col = normalized_columns.get("exchange")

        if symbol_col and exchange_col:
            for _, row in listing_data[[symbol_col, exchange_col]].dropna().iterrows():
                mapping[str(row[symbol_col]).strip().upper()] = str(row[exchange_col]).strip().upper()

    return mapping


def enrich_exchange(universe_df: pd.DataFrame) -> pd.DataFrame:
    working_df = universe_df.copy()
    working_df["exchange"] = working_df["exchange"].astype(str).str.strip().str.upper()

    unknown_mask = working_df["exchange"].isin({"", "UNKNOWN", "NAN"})
    if not unknown_mask.any():
        return working_df

    mapping = build_exchange_mapping()
    if not mapping:
        return working_df

    working_df.loc[unknown_mask, "exchange"] = (
        working_df.loc[unknown_mask, "symbol"].map(mapping).fillna("UNKNOWN")
    )
    return working_df


def preselect_universe(
    universe_df: pd.DataFrame,
    *,
    hose_top_n: int,
    other_top_n: int,
    volume_cache_path: Path,
) -> pd.DataFrame:
    working_df = enrich_exchange(universe_df)
    working_df["exchange"] = working_df["exchange"].astype(str).str.upper()

    if volume_cache_path.exists():
        cache_df = pd.read_csv(volume_cache_path)
        cache_df.columns = [str(column).strip().lower() for column in cache_df.columns]

        if {"symbol", "avg_volume"}.issubset(cache_df.columns):
            cache_df["symbol"] = cache_df["symbol"].astype(str).str.strip().str.upper()
            cache_df["avg_volume"] = pd.to_numeric(cache_df["avg_volume"], errors="coerce").fillna(0.0)
            cache_df = cache_df[["symbol", "avg_volume"]].drop_duplicates(subset=["symbol"])

            working_df = working_df.merge(cache_df, on="symbol", how="left", suffixes=("", "_cached"))
            if "avg_volume_cached" in working_df.columns:
                working_df["avg_volume_seed"] = working_df["avg_volume_cached"].fillna(0.0)
            else:
                working_df["avg_volume_seed"] = 0.0

            LOGGER.info("Using cached avg_volume to preselect universe: %s", volume_cache_path)
        else:
            working_df["avg_volume_seed"] = 0.0
    else:
        working_df["avg_volume_seed"] = 0.0
        LOGGER.warning(
            "No cached volume file found at %s; preselecting by exchange without volume ranking.",
            volume_cache_path,
        )

    hose_df = (
        working_df[working_df["exchange"] == "HOSE"]
        .sort_values(by=["avg_volume_seed", "symbol"], ascending=[False, True])
        .head(hose_top_n)
    )

    other_df = (
        working_df[working_df["exchange"] != "HOSE"]
        .sort_values(by=["avg_volume_seed", "symbol"], ascending=[False, True])
        .head(other_top_n)
    )

    selected_df = pd.concat([hose_df, other_df], ignore_index=True)
    selected_df = selected_df.drop_duplicates(subset=["symbol"]).reset_index(drop=True)
    return selected_df


def get_price_data(symbol: str) -> pd.DataFrame | None:
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=370)
        df = stock.quote.history(
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval="1D",
        )
    except Exception as exc:
        LOGGER.warning("symbol=%s history fetch failed: %s", symbol, exc)
        return None

    if df is None or df.empty:
        return None

    normalized = df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    required_columns = {"close", "volume"}
    if not required_columns.issubset(normalized.columns):
        return None

    normalized = normalized.dropna(subset=["close", "volume"]).reset_index(drop=True)
    if len(normalized) < 60:
        return None

    return normalized


def compute_metrics(price_df: pd.DataFrame) -> dict[str, float] | None:
    if price_df is None or price_df.empty or len(price_df) < 60:
        return None

    close = pd.to_numeric(price_df["close"], errors="coerce").dropna()
    volume = pd.to_numeric(price_df["volume"], errors="coerce").dropna()

    if len(close) < 60 or len(volume) < 20:
        return None

    last_price = float(close.iloc[-1])
    first_price = float(close.iloc[0])
    price_60 = float(close.iloc[-60])

    if first_price <= 0 or price_60 <= 0 or last_price <= 0:
        return None

    avg_volume_20d = float(volume.tail(20).mean())
    avg_volume_prev_20d = float(volume.tail(40).head(20).mean()) if len(volume) >= 40 else avg_volume_20d
    volume_ratio_20d = avg_volume_20d / avg_volume_prev_20d if avg_volume_prev_20d > 0 else 1.0

    return {
        "last_price": last_price,
        "avg_volume": avg_volume_20d,
        "return_3m": (last_price / price_60) - 1.0,
        "return_1y": (last_price / first_price) - 1.0,
        "volume_ratio_20d": volume_ratio_20d,
    }


def select_candidates_by_exchange(
    df: pd.DataFrame,
    hose_top_n: int = 300,
    other_top_n: int = 200,
) -> pd.DataFrame:
    working_df = df.copy()
    working_df["exchange"] = working_df["exchange"].astype(str).str.upper()

    hose_df = working_df[working_df["exchange"] == "HOSE"].sort_values(
        by=["avg_volume", "return_3m"],
        ascending=[False, False],
    ).head(hose_top_n)

    other_df = working_df[working_df["exchange"] != "HOSE"].sort_values(
        by=["avg_volume", "return_3m"],
        ascending=[False, False],
    ).head(other_top_n)

    selected_df = pd.concat([hose_df, other_df], ignore_index=True)
    return selected_df.drop_duplicates(subset=["symbol"]).reset_index(drop=True)


def main() -> None:
    configure_logging()

    config = load_config(CONFIG_PATH)
    filters = config.get("filters", {})
    selection = config.get("selection", {})
    runtime = config.get("runtime", {})

    min_avg_volume = int(filters.get("min_avg_volume", 100_000))
    min_price = float(filters.get("min_price", 3))
    top_n = int(selection.get("top_n", 10))
    hose_top_n = int(selection.get("hose_top_n", 300))
    other_top_n = int(selection.get("other_top_n", 300))
    batch_size = int(runtime.get("batch_size", 50))
    batch_sleep_seconds = float(runtime.get("batch_sleep_seconds", 10))
    request_delay_seconds = float(runtime.get("request_delay_seconds", 1.0))

    universe_df = preselect_universe(
        load_universe(UNIVERSE_PATH),
        hose_top_n=hose_top_n,
        other_top_n=other_top_n,
        volume_cache_path=RAW_SCAN_OUTPUT,
    )
    results: list[dict[str, Any]] = []

    total = len(universe_df)

    for index, row in universe_df.iterrows():
        symbol = str(row["symbol"]).strip().upper()
        exchange = str(row.get("exchange", "UNKNOWN")).strip().upper()
        sector = str(row.get("sector", "UNKNOWN")).strip().upper()

        LOGGER.info("Processing %s (%s) [%s/%s]", symbol, exchange, index + 1, total)

        price_df = get_price_data(symbol)
        metrics = compute_metrics(price_df)

        if metrics is not None:
            results.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "sector": sector,
                    **metrics,
                    "news_signal": 0.0,
                    "risk_halt_flag": 0,
                }
            )

        time.sleep(request_delay_seconds)

        if (index + 1) % batch_size == 0 and index + 1 < total:
            LOGGER.info("Sleeping batch for %s seconds", batch_sleep_seconds)
            time.sleep(batch_sleep_seconds)

    if not results:
        raise RuntimeError("Universe scan returned no valid rows.")

    scanned_df = pd.DataFrame(results)

    filtered_df = scanned_df[
        (scanned_df["avg_volume"] >= min_avg_volume)
        & (scanned_df["last_price"] >= min_price)
    ].copy()

    selected_df = select_candidates_by_exchange(
        filtered_df,
        hose_top_n=hose_top_n,
        other_top_n=other_top_n,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    symbol_news_rows: list[dict[str, Any]] = []
    symbols = selected_df["symbol"].astype(str).str.upper().tolist()

    for symbol in symbols:
        symbol_news_rows.extend(fetch_symbol_news_rows(symbol))

    market_news_rows = fetch_market_news_rows()

    aggregated_news = aggregate_news(
        symbol_news_rows=symbol_news_rows,
        market_news_rows=market_news_rows,
        symbols=symbols,
    )

    selected_df = merge_news_scores_into_universe(
        universe_df=selected_df,
        symbol_summaries=aggregated_news["symbol_summaries"],
    )

    with MARKET_NEWS_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(aggregated_news["market_summary"], file, ensure_ascii=False, indent=2)

    selected_df.to_csv(RAW_SCAN_OUTPUT, index=False)

    scored_df, top_symbols = rank_universe_from_csv(
        input_csv=RAW_SCAN_OUTPUT,
        output_csv=RANKED_OUTPUT,
        output_json=TOP10_OUTPUT,
        top_n=top_n,
    )

    LOGGER.info("Saved raw scan: %s", RAW_SCAN_OUTPUT)
    LOGGER.info("Saved ranked scores: %s", RANKED_OUTPUT)
    LOGGER.info("Top %s symbols: %s", top_n, top_symbols)
    LOGGER.info("Rows after scan=%s, after filter=%s, after exchange cut=%s", len(scanned_df), len(filtered_df), len(scored_df))


if __name__ == "__main__":
    main()
