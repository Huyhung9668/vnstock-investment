from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_chart_pattern_lab(
    *,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
) -> DictStrAny:
    normalized_symbols = symbol_payloads or {}
    normalized_trade_plans = trade_plan_payloads or {}

    chart_rows: list[DictStrAny] = []
    for symbol in sorted(set(normalized_symbols) | set(normalized_trade_plans)):
        analysis = dict(normalized_symbols.get(symbol) or {})
        trade_plan = dict(normalized_trade_plans.get(symbol) or {})
        entry_zone = dict(trade_plan.get("entry_zone") or {})
        chart_rows.append(
            {
                "symbol": str(symbol).strip().upper(),
                "trend": analysis.get("trend") or _nested(analysis, "technical_summary", "trend") or "unknown",
                "support": analysis.get("support") or _nested(analysis, "technical_summary", "support"),
                "resistance": analysis.get("resistance") or _nested(analysis, "technical_summary", "resistance"),
                "entry_zone": _entry_zone_label(entry_zone),
                "chart_status": "annotatable" if entry_zone or analysis else "needs_data",
            }
        )

    lead = chart_rows[0] if chart_rows else {}
    brief = build_analyst_brief(
        insight=(
            f"Lớp chart đang đủ dữ liệu để đánh dấu vùng giá quan trọng cho {lead.get('symbol')}."
            if lead.get("symbol")
            else "Chưa đủ dữ liệu để dựng lớp chart có ngữ cảnh."
        ),
        evidence=[f"Chart pattern lab đã chuẩn bị ngữ cảnh cho {len(chart_rows)} mã."] if chart_rows else [],
        implication="Chart nên được dùng để nhìn rõ support, resistance và nhịp phản ứng giá trước khi nâng xác suất cho một ý tưởng.",
        action="Ưu tiên vẽ hoặc gắn chart cho nhóm mã đầu danh sách để kiểm tra xem trigger có thực sự nằm ở vùng đáng hành động hay không.",
        risk="Nếu chart chưa có vùng giá rõ ràng thì mọi diễn giải kỹ thuật đều dễ trở thành cảm tính.",
    )

    return {
        "status": "ready" if chart_rows else "missing",
        "summary": f"Chart pattern lab đã chuẩn bị context cho {len(chart_rows)} mã." if chart_rows else "Chưa có chart context.",
        "rows": chart_rows,
        "analyst_brief": brief,
    }


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _entry_zone_label(entry_zone: DictStrAny) -> str:
    low = entry_zone.get("low")
    high = entry_zone.get("high")
    if low is None and high is None:
        return "chưa có vùng vào lệnh"
    return f"{low} - {high}"
