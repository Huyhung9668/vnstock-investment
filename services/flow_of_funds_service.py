from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_flow_of_funds(
    *,
    market_overview: dict[str, Any] | None,
    ranking_rows: list[dict[str, Any]] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    liquidity = _ensure_dict(normalized_market.get("liquidity_concentration"))
    top_symbols = liquidity.get("top_symbols")
    share = liquidity.get("top_n_liquidity_share")
    symbols = []
    if isinstance(top_symbols, list):
        for item in top_symbols[:5]:
            if isinstance(item, dict):
                symbol = str(item.get("symbol", "")).strip().upper()
                if symbol:
                    symbols.append(symbol)

    if not symbols and isinstance(ranking_rows, list):
        for row in ranking_rows[:5]:
            if isinstance(row, dict):
                symbol = str(row.get("symbol", "")).strip().upper()
                if symbol:
                    symbols.append(symbol)

    summary = "Dong tien chua ro."
    if symbols:
        summary = f"Dong tien hien dang tap trung vao nhom dan dat: {', '.join(symbols[:3])}."
    if share is not None:
        summary += f" Muc tap trung thanh khoan = {_fmt(share)}."

    return {
        "status": "ready" if normalized_market else "degraded",
        "summary": summary,
        "focus_symbols": symbols[:5],
        "liquidity_share": share,
    }


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)
