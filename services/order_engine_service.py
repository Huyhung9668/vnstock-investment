from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_order_engine(
    *,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    risk_engine_payload: dict[str, Any] | None,
) -> DictStrAny:
    trade_payloads = trade_plan_payloads or {}
    risk_rows = {
        str(item.get("symbol", "")).strip().upper(): dict(item)
        for item in (risk_engine_payload or {}).get("rows", [])
        if isinstance(item, dict)
    }

    rows: list[DictStrAny] = []
    for symbol, payload in sorted(trade_payloads.items()):
        if not isinstance(payload, dict):
            continue
        entry_zone = dict(payload.get("entry_zone") or {})
        target = dict(payload.get("target") or {})
        risk_row = risk_rows.get(str(symbol).strip().upper(), {})
        rows.append(
            {
                "symbol": str(symbol).strip().upper(),
                "entry_zone": _entry_zone_label(entry_zone),
                "stop_loss": payload.get("stop_loss"),
                "target_1": target.get("target_1"),
                "risk_reward": payload.get("risk_reward"),
                "risk_tier": risk_row.get("risk_tier", "unknown"),
                "position_sizing_hint": payload.get("position_sizing_hint"),
            }
        )

    lead = rows[0] if rows else {}
    brief = build_analyst_brief(
        insight=(
            f"Order engine đã chuyển insight thành khung vào lệnh trung tính cho {lead.get('symbol')}."
            if lead.get("symbol")
            else "Chưa có đủ dữ liệu để chuyển sang lớp order engine."
        ),
        evidence=[f"Có {len(rows)} kế hoạch vào lệnh đã được chuẩn hóa."] if rows else [],
        implication="Kế hoạch vào lệnh chỉ có giá trị khi entry, stop và target cùng nằm trong một câu chuyện rủi ro nhất quán.",
        action="Ưu tiên thực thi ở các mã có risk/reward còn đủ rộng và risk tier không bị đẩy lên mức cao.",
        risk="Nếu chỉ có thesis mà chưa có vùng vào lệnh và stop rõ ràng thì chưa nên xem đó là cơ hội sẵn sàng hành động.",
    )

    return {
        "status": "ready" if rows else "missing",
        "summary": f"Order engine đã chuẩn hóa {len(rows)} kịch bản vào lệnh." if rows else "Chưa có order context.",
        "rows": rows,
        "analyst_brief": brief,
    }


def _entry_zone_label(entry_zone: DictStrAny) -> str:
    low = entry_zone.get("low")
    high = entry_zone.get("high")
    strategy = str(entry_zone.get("strategy", "")).strip()
    if low is None and high is None:
        return strategy or "wait"
    return f"{low} - {high} ({strategy or 'entry'})"
