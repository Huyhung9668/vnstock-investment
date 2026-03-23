from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from vnstock import Vnstock


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch price history and generate report.")
    parser.add_argument("--symbol", required=True, help="Stock symbol, e.g. VCB")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2024-01-01")
    parser.add_argument("--end", required=True, help="End date, e.g. 2024-12-31")
    parser.add_argument("--source", default="VCI", help="Data source, default: VCI")
    return parser.parse_args()


def fetch_price_history(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    stock = Vnstock().stock(symbol=symbol.upper(), source=source)
    df = stock.quote.history(start=start, end=end)

    if df is None or df.empty:
        raise ValueError(f"No price history returned for {symbol}")

    df = df.copy()
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])

    return df


def save_price_csv(df: pd.DataFrame, symbol: str, start: str, end: str) -> Path:
    output_dir = Path("data/raw/prices")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_start = start.replace("-", "")
    safe_end = end.replace("-", "")
    output_path = output_dir / f"{symbol.lower()}_{safe_start}_{safe_end}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def save_chart(df: pd.DataFrame, symbol: str, start: str, end: str) -> Path:
    output_dir = Path("reports/charts")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_start = start.replace("-", "")
    safe_end = end.replace("-", "")
    output_path = output_dir / f"{symbol.lower()}_{safe_start}_{safe_end}.png"

    fig = plt.figure(figsize=(12, 6))
    plt.plot(df["time"], df["close"])
    plt.title(f"{symbol} Close Price")
    plt.xlabel("Time")
    plt.ylabel("Close")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return output_path


def build_summary(df: pd.DataFrame) -> dict[str, float | int | str]:
    first_close = float(df["close"].iloc[0])
    last_close = float(df["close"].iloc[-1])
    pct_change = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
    avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0
    daily_return_std = float(df["close"].pct_change().std() * 100)

    return {
        "rows": int(len(df)),
        "start_time": str(df["time"].min().date()) if "time" in df.columns else "N/A",
        "end_time": str(df["time"].max().date()) if "time" in df.columns else "N/A",
        "first_close": round(first_close, 2),
        "last_close": round(last_close, 2),
        "pct_change": round(pct_change, 2),
        "avg_volume": round(avg_volume, 2),
        "daily_volatility_pct": round(daily_return_std, 4),
    }


def build_markdown_report(
    symbol: str,
    source: str,
    start: str,
    end: str,
    summary: dict[str, float | int | str],
    csv_path: Path,
    chart_path: Path,
) -> str:
    return "\n".join(
        [
            f"# Price History - {symbol}",
            "",
            f"- **Source**: {source}",
            f"- **Period**: {start} -> {end}",
            "",
            "## Tóm tắt",
            f"- **Số ngày dữ liệu**: {summary['rows']}",
            f"- **Ngày đầu**: {summary['start_time']}",
            f"- **Ngày cuối**: {summary['end_time']}",
            f"- **Giá đóng cửa đầu kỳ**: {summary['first_close']}",
            f"- **Giá đóng cửa cuối kỳ**: {summary['last_close']}",
            f"- **Tăng/giảm toàn kỳ (%)**: {summary['pct_change']}",
            f"- **Khối lượng trung bình**: {summary['avg_volume']}",
            f"- **Biến động cơ bản ngày (%)**: {summary['daily_volatility_pct']}",
            "",
            "## Đầu ra",
            f"- **CSV**: `{csv_path}`",
            f"- **Chart**: `{chart_path}`",
            "",
            "## Ghi chú",
            "- Báo cáo này mô tả dữ liệu giá, không phải khuyến nghị đầu tư.",
            "",
        ]
    )


def save_markdown_report(symbol: str, markdown_text: str) -> Path:
    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"price_{symbol.lower()}.md"
    output_path.write_text(markdown_text, encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()

    df = fetch_price_history(
        symbol=symbol,
        start=args.start,
        end=args.end,
        source=args.source,
    )

    csv_path = save_price_csv(df, symbol=symbol, start=args.start, end=args.end)
    chart_path = save_chart(df, symbol=symbol, start=args.start, end=args.end)
    summary = build_summary(df)
    report_text = build_markdown_report(
        symbol=symbol,
        source=args.source,
        start=args.start,
        end=args.end,
        summary=summary,
        csv_path=csv_path,
        chart_path=chart_path,
    )
    report_path = save_markdown_report(symbol=symbol, markdown_text=report_text)

    print(f"Price history completed for {symbol}")
    print(f"Rows saved : {len(df)}")
    print(f"CSV file   : {csv_path}")
    print(f"Chart file : {chart_path}")
    print(f"Report file: {report_path}")


if __name__ == "__main__":
    main()