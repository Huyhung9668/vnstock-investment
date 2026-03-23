# scripts/stock_deep_dive.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from vnstock import Vnstock


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a stock deep dive report.")
    parser.add_argument("--symbol", required=True, help="Stock symbol, e.g. VCB")
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default="2024-12-31", help="End date")
    parser.add_argument("--source", default="VCI", help="Data source")
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
        return result, None if not result.empty else "Returned empty DataFrame"

    try:
        df = pd.DataFrame(result)
        return df, None if not df.empty else "Returned empty DataFrame"
    except Exception:
        return None, "Unsupported return type"


def fetch_price_history(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    stock = Vnstock().stock(symbol=symbol.upper(), source=source)
    df = stock.quote.history(start=start, end=end)

    if df is None or df.empty:
        raise ValueError(f"No price history returned for {symbol}")

    df = df.copy()
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)

    return df


def summarize_company(overview_df: pd.DataFrame | None) -> list[str]:
    if overview_df is None or overview_df.empty:
        return ["- Chưa lấy được overview doanh nghiệp."]

    row = overview_df.iloc[0].to_dict()
    preferred_keys = [
        "symbol",
        "organ_name",
        "exchange",
        "industry",
        "icb_name",
        "established_year",
        "website",
    ]

    lines = []
    for key in preferred_keys:
        if key in row and pd.notna(row[key]):
            lines.append(f"- **{key}**: {row[key]}")

    return lines or ["- Overview có dữ liệu nhưng chưa có cột tóm tắt quen thuộc."]


def summarize_price(df: pd.DataFrame) -> dict[str, float | str | int]:
    if len(df) < 2:
        raise ValueError("Price history needs at least 2 rows")

    first_close = float(df["close"].iloc[0])
    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])

    period_change_pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
    recent_change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
    avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0
    high_max = float(df["high"].max()) if "high" in df.columns else last_close
    low_min = float(df["low"].min()) if "low" in df.columns else last_close

    return {
        "rows": len(df),
        "start_date": str(df["time"].min().date()) if "time" in df.columns else "N/A",
        "end_date": str(df["time"].max().date()) if "time" in df.columns else "N/A",
        "first_close": round(first_close, 2),
        "last_close": round(last_close, 2),
        "recent_change_pct": round(recent_change_pct, 2),
        "period_change_pct": round(period_change_pct, 2),
        "avg_volume": round(avg_volume, 2),
        "high_max": round(high_max, 2),
        "low_min": round(low_min, 2),
    }


def recent_price_behavior(summary: dict[str, float | str | int]) -> list[str]:
    recent_change_pct = float(summary["recent_change_pct"])
    period_change_pct = float(summary["period_change_pct"])

    lines: list[str] = []

    if recent_change_pct > 1:
        lines.append("- Giá gần nhất đang tăng rõ trong ngắn hạn.")
    elif recent_change_pct > 0:
        lines.append("- Giá gần nhất đang nhích tăng nhẹ.")
    elif recent_change_pct < -1:
        lines.append("- Giá gần nhất đang chịu áp lực giảm tương đối rõ.")
    else:
        lines.append("- Giá gần nhất đang đi ngang hoặc biến động hẹp.")

    if period_change_pct > 10:
        lines.append("- Toàn giai đoạn đang nghiêng về xu hướng tăng đáng kể.")
    elif period_change_pct > 0:
        lines.append("- Toàn giai đoạn vẫn đang giữ được trạng thái tích cực nhẹ.")
    elif period_change_pct < -10:
        lines.append("- Toàn giai đoạn cho thấy trạng thái suy yếu rõ.")
    else:
        lines.append("- Toàn giai đoạn chưa tạo xu hướng đủ mạnh để kết luận chắc chắn.")

    return lines


def strengths_and_risks(
    company_overview_df: pd.DataFrame | None,
    price_summary: dict[str, float | str | int],
) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    risks: list[str] = []

    if company_overview_df is not None and not company_overview_df.empty:
        row = company_overview_df.iloc[0].to_dict()
        if pd.notna(row.get("industry")) or pd.notna(row.get("icb_name")):
            strengths.append("- Có dữ liệu ngành/ngữ cảnh doanh nghiệp để hỗ trợ diễn giải.")
        if pd.notna(row.get("website")):
            strengths.append("- Có website doanh nghiệp để đối chiếu thông tin gốc khi cần.")

    period_change_pct = float(price_summary["period_change_pct"])
    recent_change_pct = float(price_summary["recent_change_pct"])

    if period_change_pct > 0:
        strengths.append("- Dữ liệu giá toàn kỳ chưa phủ nhận hoàn toàn trạng thái tích cực.")
    else:
        risks.append("- Dữ liệu giá toàn kỳ đang yếu, cần cẩn trọng khi diễn giải.")

    if abs(recent_change_pct) > 3:
        risks.append("- Biến động ngắn hạn khá mạnh, cần kiểm tra thêm volume và bối cảnh thị trường.")

    if not strengths:
        strengths.append("- Hiện mới có lợi thế ở việc đã gom được dữ liệu cơ bản để theo dõi tiếp.")

    if not risks:
        risks.append("- Chưa thấy rủi ro nổi bật từ số liệu hiện có, nhưng vẫn cần xác nhận thêm dữ liệu cơ bản sâu hơn.")

    return strengths, risks


def build_report(
    symbol: str,
    source: str,
    company_overview_df: pd.DataFrame | None,
    company_note: str | None,
    price_summary: dict[str, float | str | int],
    strengths: list[str],
    risks: list[str],
) -> str:
    who_is_the_company = "\n".join(summarize_company(company_overview_df))
    price_behavior = "\n".join(
        [
            f"- **Giai đoạn**: {price_summary['start_date']} → {price_summary['end_date']}",
            f"- **Số phiên**: {price_summary['rows']}",
            f"- **Giá đầu kỳ**: {price_summary['first_close']}",
            f"- **Giá cuối kỳ**: {price_summary['last_close']}",
            f"- **Biến động phiên gần nhất (%)**: {price_summary['recent_change_pct']}",
            f"- **Biến động toàn kỳ (%)**: {price_summary['period_change_pct']}",
            f"- **Đỉnh dữ liệu**: {price_summary['high_max']}",
            f"- **Đáy dữ liệu**: {price_summary['low_min']}",
            f"- **Khối lượng trung bình**: {price_summary['avg_volume']}",
            "",
            *recent_price_behavior(price_summary),
        ]
    )

    strengths_text = "\n".join(strengths)
    risks_text = "\n".join(risks)

    next_checks = "\n".join(
        [
            "- Kiểm tra thêm báo cáo tài chính hoặc chỉ số cơ bản nếu nguồn hỗ trợ.",
            "- Đối chiếu diễn biến giá với trạng thái chung của thị trường.",
            "- Theo dõi thêm vài phiên tới để xác nhận tín hiệu ngắn hạn.",
            "- Không biến kết quả hiện tại thành khuyến nghị đầu tư chắc chắn.",
        ]
    )

    sections = [
        f"# Stock Deep Dive - {symbol}",
        "",
        f"- **Source**: {source}",
        "",
        "## 1. Doanh nghiệp là ai",
        who_is_the_company,
        "",
        "## 2. Giá đang hành xử ra sao",
        price_behavior,
        "",
        "## 3. Điểm mạnh / yếu từ dữ liệu hiện có",
        "### Điểm mạnh",
        strengths_text,
        "",
        "### Điểm cần lưu ý",
        risks_text,
        "",
        "## 4. Cần kiểm tra gì tiếp theo",
        next_checks,
        "",
    ]

    if company_note:
        sections.extend(["## Ghi chú dữ liệu doanh nghiệp", f"- {company_note}", ""])

    return "\n".join(sections)


def save_report(symbol: str, markdown_text: str) -> Path:
    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"deep_dive_{symbol.lower()}.md"
    output_path.write_text(markdown_text, encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()

    stock_client = get_stock_client(symbol=symbol, source=args.source)
    company_client = get_company_client(stock_client)
    overview_df, overview_note = safe_call(company_client, "overview")

    price_df = fetch_price_history(
        symbol=symbol,
        start=args.start,
        end=args.end,
        source=args.source,
    )
    price_summary = summarize_price(price_df)
    strengths, risks = strengths_and_risks(overview_df, price_summary)

    report_text = build_report(
        symbol=symbol,
        source=args.source,
        company_overview_df=overview_df,
        company_note=overview_note,
        price_summary=price_summary,
        strengths=strengths,
        risks=risks,
    )
    output_path = save_report(symbol=symbol, markdown_text=report_text)

    print(f"Stock deep dive completed for {symbol}")
    print(f"Report file: {output_path}")


if __name__ == "__main__":
    main()