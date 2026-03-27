from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
)


def _clear_runtime_proxies() -> None:
    for key in PROXY_ENV_KEYS:
        if key in os.environ:
            os.environ.pop(key, None)


_clear_runtime_proxies()

import daily_run
from scripts import universe_scan
from services.ranking_service import rank_universe_dataframe


RAW_SCAN_OUTPUT = PROJECT_ROOT / "data" / "derived" / "universe_scan_raw.csv"
RANKED_OUTPUT = PROJECT_ROOT / "data" / "derived" / "universe_scores.csv"
TOP_OUTPUT = PROJECT_ROOT / "data" / "derived" / "top10_symbols.json"
GENERATED_CONFIG_ROOT = PROJECT_ROOT / "config" / "generated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank a watchlist subset, keep the best symbols, then run daily terminal analysis.",
    )
    parser.add_argument("--config-dir", default=str(PROJECT_ROOT / "config" / "test20"))
    parser.add_argument("--watchlist-limit", type=int, default=20)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--keep-telegram", action="store_true")
    return parser.parse_args()


def _load_yaml(path: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    with path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return dict(payload) if isinstance(payload, dict) else dict(default or {})


def _save_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)


def _load_symbols(watchlist_payload: dict[str, Any], limit: int) -> list[str]:
    raw_symbols = watchlist_payload.get("symbols", [])
    if not isinstance(raw_symbols, list):
        return []
    symbols: list[str] = []
    seen: set[str] = set()
    for item in raw_symbols:
        symbol = str(item).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
        if len(symbols) >= limit:
            break
    return symbols


def _candidate_config_dirs(source_config_dir: Path, watchlist_limit: int) -> list[Path]:
    root_config_dir = PROJECT_ROOT / "config"
    candidates: list[Path] = [source_config_dir]

    if source_config_dir == root_config_dir:
        candidates.extend(
            [
                root_config_dir / f"test{watchlist_limit}",
                root_config_dir / "test100",
                root_config_dir / "test50",
                root_config_dir / "test20",
            ]
        )
    elif source_config_dir.parent == root_config_dir:
        candidates.extend(
            [
                root_config_dir / f"test{watchlist_limit}",
                root_config_dir / "test100",
                root_config_dir / "test50",
                root_config_dir / "test20",
                root_config_dir,
            ]
        )

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(resolved)
    return unique_candidates


def _resolve_source_config_dir(source_config_dir: Path, watchlist_limit: int, top_n: int) -> Path:
    fallback_dir: Path | None = None
    for candidate in _candidate_config_dirs(source_config_dir, watchlist_limit):
        watchlist_payload = _load_yaml(candidate / "watchlist.yaml")
        symbols = _load_symbols(watchlist_payload, watchlist_limit)
        if len(symbols) >= watchlist_limit:
            return candidate
        if len(symbols) >= top_n and fallback_dir is None:
            fallback_dir = candidate
    return fallback_dir or source_config_dir


def _scan_watchlist(symbols: list[str]) -> pd.DataFrame:
    request_delay_seconds = 1.1
    batch_size = 45
    batch_sleep_seconds = 20.0
    rows: list[dict[str, Any]] = []
    for index, symbol in enumerate(symbols, start=1):
        print(f"[scan] {index}/{len(symbols)} {symbol}")
        price_df = _get_price_data_with_retry(symbol)
        metrics = universe_scan.compute_metrics(price_df)
        if metrics is None:
            time.sleep(request_delay_seconds)
            continue
        rows.append(
            {
                "symbol": symbol,
                "exchange": "UNKNOWN",
                "sector": "UNKNOWN",
                **metrics,
                "news_signal": 0.0,
                "risk_halt_flag": 0,
            }
        )
        time.sleep(request_delay_seconds)
        if index % batch_size == 0 and index < len(symbols):
            print(f"[scan] sleep {batch_sleep_seconds:.0f}s to avoid rate limit")
            time.sleep(batch_sleep_seconds)

    if not rows:
        raise RuntimeError("Watchlist scan returned no usable rows.")

    df = pd.DataFrame(rows)
    RAW_SCAN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_SCAN_OUTPUT, index=False)
    return df


def _get_price_data_with_retry(symbol: str, max_attempts: int = 3) -> pd.DataFrame | None:
    backoff_seconds = [0.0, 18.0, 30.0]
    for attempt in range(max_attempts):
        price_df = universe_scan.get_price_data(symbol)
        if price_df is not None:
            return price_df
        sleep_for = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
        if sleep_for > 0 and attempt < max_attempts - 1:
            print(f"[scan] retry {symbol} after {sleep_for:.0f}s")
            time.sleep(sleep_for)
    return None


def _write_rank_outputs(scanned_df: pd.DataFrame, top_n: int) -> list[str]:
    ranked_df, _ = rank_universe_dataframe(scanned_df, top_n=max(top_n, 10))
    ranked_df = _prefer_long_candidates(ranked_df)
    top_symbols = ranked_df.head(top_n)["symbol"].astype(str).tolist()
    RANKED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ranked_df.to_csv(RANKED_OUTPUT, index=False)
    with TOP_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(top_symbols, file, ensure_ascii=False, indent=2)
    return top_symbols


def _prefer_long_candidates(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    day_change = _numeric_series(working, "day_change_pct")
    ret_3m = _numeric_series(working, "return_3m")
    volume_ratio = _numeric_series(working, "volume_ratio_20d")
    score = _numeric_series(working, "score", fallback="final_score")

    working["long_candidate_flag"] = ((day_change > 0) & (ret_3m > 0)).astype(int)
    working["long_priority_score"] = (
        working["long_candidate_flag"] * 10
        + score * 3
        + day_change.clip(lower=-10, upper=10)
        + ret_3m.clip(lower=-1, upper=1) * 10
        + volume_ratio.clip(lower=0, upper=5)
    )
    working["sort_score"] = score
    working["sort_day_change_pct"] = day_change
    working["sort_return_3m"] = ret_3m
    working = working.sort_values(
        by=["long_candidate_flag", "long_priority_score", "sort_score", "sort_day_change_pct", "sort_return_3m", "avg_volume"],
        ascending=[False, False, False, False, False, False],
    ).reset_index(drop=True)
    working["rank"] = range(1, len(working) + 1)
    return working



def _numeric_series(df: pd.DataFrame, column: str, fallback: str | None = None) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    if fallback and fallback in df.columns:
        return pd.to_numeric(df[fallback], errors="coerce").fillna(0.0)
    return pd.Series(0.0, index=df.index)

def _prepare_generated_config(*, source_config_dir: Path, ranked_symbols: list[str], top_n: int, keep_telegram: bool) -> Path:
    runtime_payload = _load_yaml(source_config_dir / "runtime.yaml")
    sources_payload = _load_yaml(source_config_dir / "sources.yaml")
    universe_payload = _load_yaml(source_config_dir / "universe.yaml")
    sources_payload = _normalize_sources_payload(sources_payload)

    runtime_payload.setdefault("selection", {})
    runtime_payload["selection"]["mode"] = "watchlist"
    runtime_payload["selection"]["top_n"] = int(top_n)
    runtime_payload["selection"]["fallback_to_watchlist"] = True

    notification_payload = runtime_payload.setdefault("notification", {})
    telegram_payload = notification_payload.setdefault("telegram", {})
    if not keep_telegram:
        telegram_payload["enabled"] = False

    generated_dir = GENERATED_CONFIG_ROOT / f"watchlist_{len(ranked_symbols)}_top_{top_n}"
    if generated_dir.exists():
        shutil.rmtree(generated_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)

    _save_yaml(generated_dir / "runtime.yaml", runtime_payload)
    _save_yaml(generated_dir / "sources.yaml", sources_payload)
    _save_yaml(generated_dir / "watchlist.yaml", {"symbols": ranked_symbols})
    if universe_payload:
        _save_yaml(generated_dir / "universe.yaml", universe_payload)
    return generated_dir


def _normalize_sources_payload(payload: dict[str, Any]) -> dict[str, Any]:
    providers = payload.get("providers")
    if isinstance(providers, dict):
        normalized = dict(payload)
        services = normalized.get("services")
        if not isinstance(services, dict):
            normalized["services"] = {
                "market": providers.get("primary", "free"),
                "news": providers.get("primary", "free"),
                "financials": providers.get("primary", "free"),
            }
        return normalized

    provider = str(payload.get("provider") or "free").strip().lower() or "free"
    return {
        "providers": {
            "primary": provider,
            "fallback": provider,
        },
        "services": {
            "market": str(payload.get("market_data") or provider).strip().lower() or provider,
            "news": str(payload.get("news") or provider).strip().lower() or provider,
            "financials": str(payload.get("financials") or provider).strip().lower() or provider,
        },
    }


def _run_daily(config_dir: Path) -> dict[str, Any]:
    original_parse_args = daily_run.parse_args
    try:
        daily_run.parse_args = lambda: type("Args", (), {"config_dir": str(config_dir)})()
        return daily_run.main()
    finally:
        daily_run.parse_args = original_parse_args


def main() -> int:
    args = parse_args()
    source_config_dir = _resolve_source_config_dir(Path(args.config_dir).resolve(), args.watchlist_limit, args.top_n)
    watchlist_payload = _load_yaml(source_config_dir / "watchlist.yaml")
    symbols = _load_symbols(watchlist_payload, args.watchlist_limit)
    if len(symbols) < args.top_n:
        raise ValueError(
            f"Need at least {args.top_n} symbols, got {len(symbols)} from {source_config_dir / 'watchlist.yaml'}"
        )

    _clear_runtime_proxies()
    daily_run.load_dotenv_if_present()
    _clear_runtime_proxies()
    scanned_df = _scan_watchlist(symbols)
    top_symbols = _write_rank_outputs(scanned_df, top_n=args.top_n)

    ranked_symbols = pd.read_csv(RANKED_OUTPUT)["symbol"].astype(str).str.upper().drop_duplicates().tolist()
    generated_config_dir = _prepare_generated_config(
        source_config_dir=source_config_dir,
        ranked_symbols=ranked_symbols,
        top_n=args.top_n,
        keep_telegram=args.keep_telegram,
    )

    summary = _run_daily(generated_config_dir)

    print("WATCHLIST TOP-SELECTION TERMINAL RUN")
    print(f"- source_config_dir={source_config_dir}")
    print(f"- watchlist_limit={args.watchlist_limit}")
    print(f"- top_symbols={top_symbols}")
    print(f"- generated_config_dir={generated_config_dir}")
    print(f"- run_id={summary.get('run_id')}")
    headline = str(summary.get('headline', ''))
    print(f"- headline={headline}")
    print(f"- output_dir={summary.get('artifacts_output_dir')}")
    print(f"- manifest_path={summary.get('manifest_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
