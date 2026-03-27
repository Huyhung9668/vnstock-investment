from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_foreign_flow_decoder(
    *,
    market_overview: dict[str, Any] | None,
    ranking_rows: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    rows = [dict(item) for item in (ranking_rows or []) if isinstance(item, dict)]
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    liquidity = _ensure_dict(normalized_market.get("liquidity_concentration"))
    top_symbols = _top_symbols(liquidity, rows)
    share = _to_float(liquidity.get("top_n_liquidity_share"))
    regime = _text(_ensure_dict(normalized_market.get("regime")).get("regime")).lower()

    structural_vs_tactical = "tactical" if regime == "risk_off" or (share is not None and share >= 0.65) else "structural"
    fx_link = (
        "Dòng tiền ngoại đang có dấu hiệu giao dịch thận trọng hơn, phù hợp với bối cảnh tỷ giá cần được theo dõi sát."
        if regime == "risk_off"
        else "Nếu tỷ giá ổn định, xác suất dòng tiền ngoại quay lại các mã dẫn dắt sẽ tích cực hơn."
    )
    supported = _sector_buckets(top_symbols, positive=True)
    warned = _sector_buckets(top_symbols, positive=False)
    summary = (
        f"Dòng tiền tập trung vào {', '.join(top_symbols[:3])}; cấu trúc hiện nghiêng về {structural_vs_tactical} flow hơn là lan tỏa rộng."
        if top_symbols
        else "Chưa có đủ dữ liệu để đọc vị khối ngoại theo nghĩa cấu trúc."
    )
    if normalized_warnings:
        summary += " Một phần kết luận đang dùng proxy từ thanh khoản và mức tập trung dòng tiền."

    return {
        "status": "ready" if normalized_market else "degraded",
        "net_flow_summary": summary,
        "structural_vs_tactical_flow": structural_vs_tactical,
        "top_supported_sectors": supported,
        "top_warned_sectors": warned,
        "fx_link": fx_link,
        "analyst_brief": build_analyst_brief(
            insight="Khối ngoại nên được đọc theo hướng hành vi dòng tiền, không chỉ nhìn mua ròng hay bán ròng của một phiên.",
            evidence=[summary, fx_link],
            implication="Nếu dòng tiền tiếp tục chỉ tập trung vào một cụm hẹp, xác suất hình thành xu hướng bền vẫn chưa cao.",
            action="Theo dõi nhóm dẫn dắt có thanh khoản tốt trước khi mở rộng sang nhóm beta cao hoặc nhóm đầu cơ.",
            risk="Dòng tiền tactical rất dễ đảo chiều khi biến số tỷ giá hoặc tâm lý thị trường xấu đi.",
        ),
    }


def _top_symbols(liquidity: DictStrAny, rows: list[DictStrAny]) -> list[str]:
    symbols: list[str] = []
    top_items = liquidity.get("top_symbols")
    if isinstance(top_items, list):
        for item in top_items[:5]:
            if isinstance(item, dict):
                symbol = _text(item.get("symbol")).upper()
                if symbol:
                    symbols.append(symbol)
    if not symbols:
        for row in rows[:5]:
            symbol = _text(row.get("symbol")).upper()
            if symbol:
                symbols.append(symbol)
    return symbols[:5]


def _sector_buckets(symbols: list[str], *, positive: bool) -> list[str]:
    if not symbols:
        return []
    return (["Ngân hàng", "Chứng khoán", "Bất động sản"] if positive else ["Đầu cơ beta cao", "Nhóm yếu thanh khoản", "Mã chưa có xác nhận"])[: min(3, len(symbols))]


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
