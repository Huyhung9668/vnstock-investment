from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from vnstock import Vnstock


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build company profile report.")
    parser.add_argument("--symbol", required=True, help="Stock symbol, e.g. VCB")
    parser.add_argument("--source", default="VCI", help="Data source, default: VCI")
    return parser.parse_args()


def get_stock_client(symbol: str, source: str) -> Any:
    return Vnstock().stock(symbol=symbol.upper(), source=source)


def get_company_client(stock_client: Any) -> Any:
    company_client = getattr(stock_client, "company", None)
    if company_client is None:
        raise AttributeError("stock.company is not available in this vnstock version")
    return company_client() if callable(company_client) else company_client


def safe_call(client: Any, method_name: str) -> tuple[pd.DataFrame | None, str | None]:
    method = getattr(client, method_name, None)
    if method is None:
        return None, f"Method `{method_name}` is not supported"

    try:
        result = method()
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

    if result is None:
        return None, "Returned None"

    if isinstance(result, pd.DataFrame):
        if result.empty:
            return result, "Returned empty DataFrame"
        return result, None

    try:
        df = pd.DataFrame(result)
        if df.empty:
            return df, "Returned empty DataFrame"
        return df, None
    except Exception:
        return None, "Unsupported return type"


def dataframe_to_markdown(df: pd.DataFrame | None, max_rows: int = 10) -> str:
    if df is None:
        return "_Không có dữ liệu._"

    if df.empty:
        return "_Nguồn trả về rỗng._"

    preview = df.head(max_rows).copy()

    try:
        return preview.to_markdown(index=False)
    except Exception:
        return dataframe_to_plain_markdown(preview)


def dataframe_to_plain_markdown(df: pd.DataFrame) -> str:
    columns = [str(column) for column in df.columns]
    lines: list[str] = []

    for row_index, (_, row) in enumerate(df.iterrows(), start=1):
        lines.append(f"### Dòng {row_index}")
        for column in columns:
            value = row[column]
            display_value = "" if pd.isna(value) else str(value)
            lines.append(f"- **{column}**: {display_value}")
        lines.append("")

    return "\n".join(lines).strip() or "_Không có dữ liệu._"


def summarize_overview(df: pd.DataFrame | None) -> list[str]:
    if df is None or df.empty:
        return ["- Không lấy được overview."]

    row = df.iloc[0].to_dict()
    keys_of_interest = [
        "symbol",
        "organ_name",
        "company_name",
        "short_name",
        "exchange",
        "industry",
        "icb_name",
        "established_year",
        "no_employees",
        "website",
    ]

    lines: list[str] = []
    for key in keys_of_interest:
        if key in row and pd.notna(row[key]):
            lines.append(f"- **{key}**: {row[key]}")

    return lines or ["- Overview có dữ liệu nhưng không có cột tóm tắt quen thuộc."]


def build_report(
    symbol: str,
    source: str,
    overview_df: pd.DataFrame | None,
    shareholders_df: pd.DataFrame | None,
    news_df: pd.DataFrame | None,
    notes: dict[str, str | None],
) -> str:
    sections: list[str] = [
        f"# Company Profile - {symbol}",
        "",
        f"- **Source**: {source}",
        "",
        "## Tóm tắt doanh nghiệp",
        *summarize_overview(overview_df),
        "",
        "## Overview",
        dataframe_to_markdown(overview_df, max_rows=5),
        "",
    ]

    if notes.get("overview"):
        sections.extend(["**Ghi chú overview:**", f"- {notes['overview']}", ""])

    sections.extend(
        [
            "## Cổ đông lớn",
            dataframe_to_markdown(shareholders_df, max_rows=10),
            "",
        ]
    )
    if notes.get("shareholders"):
        sections.extend(["**Ghi chú shareholders:**", f"- {notes['shareholders']}", ""])

    sections.extend(
        [
            "## Tin tức / thông tin gần nhất",
            dataframe_to_markdown(news_df, max_rows=10),
            "",
        ]
    )
    if notes.get("news"):
        sections.extend(["**Ghi chú news:**", f"- {notes['news']}", ""])

    sections.extend(
        [
            "## Ghi chú",
            "- Nếu một phần không có dữ liệu, báo cáo giữ nguyên và ghi rõ trạng thái.",
            "- Báo cáo này là tổng hợp dữ liệu, không phải khuyến nghị đầu tư.",
            "",
        ]
    )

    return "\n".join(sections)


def save_report(symbol: str, markdown_text: str) -> Path:
    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"company_{symbol.lower()}.md"
    output_path.write_text(markdown_text, encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()
    source = args.source

    stock_client = get_stock_client(symbol=symbol, source=source)
    company_client = get_company_client(stock_client)

    overview_df, overview_note = safe_call(company_client, "overview")
    shareholders_df, shareholders_note = safe_call(company_client, "shareholders")
    news_df, news_note = safe_call(company_client, "news")

    markdown_text = build_report(
        symbol=symbol,
        source=source,
        overview_df=overview_df,
        shareholders_df=shareholders_df,
        news_df=news_df,
        notes={
            "overview": overview_note,
            "shareholders": shareholders_note,
            "news": news_note,
        },
    )

    output_path = save_report(symbol=symbol, markdown_text=markdown_text)

    print(f"Company profile completed for {symbol}")
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()