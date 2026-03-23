# scripts/market_overview.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from vnstock import Vnstock


TEMPLATE_PATH = Path("reports/templates/market_overview_template.md")
REPORT_PATH = Path("reports/market_overview.md")
PRICES_DIR = Path("data/raw/prices")


@dataclass
class IndexSummary:
    symbol: str
    start_date: str
    end_date: str
    rows: int
    last_close: float
    day_change_pct: float
    period_change_pct: float
    avg_volume: float


@dataclass
class BreadthSummary:
    total_symbols: int
    advances: int
    declines: int
    unchanged: int
    avg_volume: float | None


def fetch_index_history(
    symbol: str = "VNINDEX",
    start: str = "2024-01-01",
    end: str = "2025-12-31",
    source: str = "VCI",
) -> pd.DataFrame:
    stock = Vnstock().stock(symbol=symbol, source=source)
    df = stock.quote.history(start=start, end=end)

    if df is None or df.empty:
        raise ValueError(f"No index data returned for {symbol}")

    df = df.copy()
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)

    return df


def summarize_index(symbol: str, df: pd.DataFrame) -> IndexSummary:
    if len(df) < 2:
        raise ValueError("Index history needs at least 2 rows")

    first_close = float(df["close"].iloc[0])
    prev_close = float(df["close"].iloc[-2])
    last_close = float(df["close"].iloc[-1])

    day_change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
    period_change_pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
    avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0

    start_date = str(df["time"].min().date()) if "time" in df.columns else "N/A"
    end_date = str(df["time"].max().date()) if "time" in df.columns else "N/A"

    return IndexSummary(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        rows=len(df),
        last_close=round(last_close, 2),
        day_change_pct=round(day_change_pct, 2),
        period_change_pct=round(period_change_pct, 2),
        avg_volume=round(avg_volume, 2),
    )


def iter_price_files(prices_dir: Path) -> Iterable[Path]:
    if not prices_dir.exists():
        return []
    return sorted(prices_dir.glob("*.csv"))


def load_recent_price_pairs(file_path: Path) -> tuple[str, float, float, float | None] | None:
    try:
        df = pd.read_csv(file_path)
    except Exception:
        return None

    required_columns = {"close"}
    if not required_columns.issubset(df.columns) or len(df) < 2:
        return None

    symbol = file_path.stem.split("_")[0].upper()
    prev_close = float(df["close"].iloc[-2])
    last_close = float(df["close"].iloc[-1])

    avg_volume = None
    if "volume" in df.columns and not df["volume"].dropna().empty:
        avg_volume = float(df["volume"].tail(20).mean())

    return symbol, prev_close, last_close, avg_volume


def summarize_breadth_from_cache(prices_dir: Path) -> BreadthSummary | None:
    records = []
    for file_path in iter_price_files(prices_dir):
        record = load_recent_price_pairs(file_path)
        if record is not None:
            records.append(record)

    if not records:
        return None

    advances = sum(1 for _, prev_close, last_close, _ in records if last_close > prev_close)
    declines = sum(1 for _, prev_close, last_close, _ in records if last_close < prev_close)
    unchanged = sum(1 for _, prev_close, last_close, _ in records if last_close == prev_close)

    volumes = [avg_volume for _, _, _, avg_volume in records if avg_volume is not None]
    avg_volume = round(sum(volumes) / len(volumes), 2) if volumes else None

    return BreadthSummary(
        total_symbols=len(records),
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        avg_volume=avg_volume,
    )


def load_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")

    return """# Market Overview

## Dữ liệu
{data_section}

## Diễn giải
{interpretation_section}

## Điều cần theo dõi tiếp
{watchlist_section}
"""


def build_data_section(index_summary: IndexSummary, breadth_summary: BreadthSummary | None) -> str:
    lines = [
        f"- Chỉ số: **{index_summary.symbol}**",
        f"- Giai đoạn dữ liệu: **{index_summary.start_date} → {index_summary.end_date}**",
        f"- Số phiên: **{index_summary.rows}**",
        f"- Điểm đóng cửa gần nhất: **{index_summary.last_close}**",
        f"- Biến động phiên gần nhất: **{index_summary.day_change_pct}%**",
        f"- Biến động toàn kỳ: **{index_summary.period_change_pct}%**",
        f"- Khối lượng trung bình: **{index_summary.avg_volume}**",
    ]

    if breadth_summary is None:
        lines.extend(
            [
                "",
                "- Breadth: **chưa có dữ liệu cache đủ để tính advances / declines**",
                "- Gợi ý: chạy batch price history cho nhiều mã để bổ sung breadth",
            ]
        )
    else:
        lines.extend(
            [
                "",
                f"- Breadth sample: **{breadth_summary.total_symbols} mã**",
                f"- Advances: **{breadth_summary.advances}**",
                f"- Declines: **{breadth_summary.declines}**",
                f"- Unchanged: **{breadth_summary.unchanged}**",
            ]
        )
        if breadth_summary.avg_volume is not None:
            lines.append(f"- Khối lượng trung bình mẫu breadth: **{breadth_summary.avg_volume}**")

    return "\n".join(lines)


def build_interpretation_section(
    index_summary: IndexSummary,
    breadth_summary: BreadthSummary | None,
) -> str:
    lines: list[str] = []

    if index_summary.day_change_pct > 1:
        lines.append("- Chỉ số đang có nhịp tăng mạnh trong phiên gần nhất.")
    elif index_summary.day_change_pct > 0:
        lines.append("- Chỉ số đang tăng nhẹ trong phiên gần nhất.")
    elif index_summary.day_change_pct < -1:
        lines.append("- Chỉ số đang chịu áp lực giảm đáng kể trong phiên gần nhất.")
    else:
        lines.append("- Chỉ số đang dao động hẹp, chưa cho tín hiệu mạnh trong phiên gần nhất.")

    if index_summary.period_change_pct > 5:
        lines.append("- Toàn kỳ đang nghiêng về xu hướng tích cực.")
    elif index_summary.period_change_pct < -5:
        lines.append("- Toàn kỳ đang nghiêng về xu hướng suy yếu.")
    else:
        lines.append("- Toàn kỳ chưa cho thấy xu hướng quá mạnh, cần thêm ngữ cảnh theo nhóm ngành và dòng tiền.")

    if breadth_summary is None:
        lines.append("- Chưa có breadth đủ rộng, nên độ chắc chắn của diễn giải nội bộ thị trường còn hạn chế.")
    else:
        if breadth_summary.advances > breadth_summary.declines:
            lines.append("- Breadth sample nghiêng về bên tăng, cho thấy độ lan tỏa tương đối tích cực.")
        elif breadth_summary.advances < breadth_summary.declines:
            lines.append("- Breadth sample nghiêng về bên giảm, cho thấy áp lực bán lan rộng hơn.")
        else:
            lines.append("- Breadth sample cân bằng, thị trường đang thiếu độ phân hóa rõ.")

    lines.append("- Đây là diễn giải dữ liệu, không phải khuyến nghị đầu tư tuyệt đối.")
    return "\n".join(lines)


def build_watchlist_section(
    index_summary: IndexSummary,
    breadth_summary: BreadthSummary | None,
) -> str:
    lines = [
        "- Theo dõi thêm 3–5 phiên tiếp theo để xác nhận độ bền của hướng đi hiện tại.",
        "- Đối chiếu chỉ số với breadth để xem đà tăng/giảm có lan tỏa thật hay không.",
        "- Bổ sung dữ liệu nhóm ngành dẫn dắt nếu cần báo cáo sâu hơn.",
    ]

    if breadth_summary is None:
        lines.append("- Ưu tiên tạo cache giá cho nhiều mã để có advances/declines/volume breadth.")
    elif breadth_summary.declines > breadth_summary.advances:
        lines.append("- Theo dõi rủi ro suy yếu nội tại: chỉ số có thể không phản ánh hết độ yếu của phần còn lại thị trường.")
    else:
        lines.append("- Theo dõi xem số mã tăng có tiếp tục duy trì cao hơn số mã giảm trong các phiên tới không.")

    if abs(index_summary.day_change_pct) > 2:
        lines.append("- Phiên gần nhất biến động khá mạnh, nên kiểm tra thêm volume xác nhận và độ lặp lại của biến động.")

    return "\n".join(lines)


def render_report(
    template: str,
    data_section: str,
    interpretation_section: str,
    watchlist_section: str,
) -> str:
    return template.format(
        data_section=data_section,
        interpretation_section=interpretation_section,
        watchlist_section=watchlist_section,
    )


def save_report(markdown_text: str) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(markdown_text, encoding="utf-8")
    return REPORT_PATH


def main() -> None:
    index_df = fetch_index_history()
    index_summary = summarize_index(symbol="VNINDEX", df=index_df)
    breadth_summary = summarize_breadth_from_cache(PRICES_DIR)

    template = load_template()
    report_text = render_report(
        template=template,
        data_section=build_data_section(index_summary, breadth_summary),
        interpretation_section=build_interpretation_section(index_summary, breadth_summary),
        watchlist_section=build_watchlist_section(index_summary, breadth_summary),
    )
    output_path = save_report(report_text)

    print("Market overview completed.")
    print(f"Report file: {output_path}")
    if breadth_summary is None:
        print("Breadth: no cached multi-symbol prices yet.")
    else:
        print(
            f"Breadth sample: {breadth_summary.total_symbols} | "
            f"advances={breadth_summary.advances} | "
            f"declines={breadth_summary.declines}"
        )


if __name__ == "__main__":
    main()