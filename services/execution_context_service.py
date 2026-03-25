from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_execution_context(
    *,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    risk_engine_payload: dict[str, Any] | None,
    portfolio_audit_payload: dict[str, Any] | None,
) -> DictStrAny:
    trade_payloads = trade_plan_payloads or {}
    risk_payload = dict(risk_engine_payload or {})
    portfolio_payload = dict(portfolio_audit_payload or {})

    rows: list[DictStrAny] = []
    for symbol, payload in sorted(trade_payloads.items()):
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "symbol": str(symbol).strip().upper(),
                "setup_type": payload.get("setup_type"),
                "risk_reward": payload.get("risk_reward"),
                "degraded_mode": bool(payload.get("degraded_mode")),
                "position_sizing_hint": payload.get("position_sizing_hint"),
            }
        )

    best_symbol = rows[0]["symbol"] if rows else ""
    posture = str(portfolio_payload.get("posture", "balanced")).strip()
    portfolio_risk = str(risk_payload.get("portfolio_risk", "medium")).strip()
    brief = build_analyst_brief(
        insight=(
            f"Lớp execution hiện cho phép ưu tiên xây kịch bản vào lệnh cho {best_symbol}, nhưng với posture {posture}."
            if best_symbol else "Chưa có đủ điều kiện execution để chuyển từ insight sang hành động."
        ),
        evidence=[
            f"Portfolio posture = {posture}.",
            f"Portfolio risk = {portfolio_risk}.",
            f"Có {len(rows)} kế hoạch giao dịch được tạo.",
        ],
        implication="Quyết định vào lệnh nên đi sau cả lớp market context lẫn risk context, không chỉ dựa vào một setup riêng lẻ.",
        action="Chỉ kích hoạt lệnh ở những mã đầu danh sách khi giá xác nhận vùng vào và tỷ lệ lợi nhuận/rủi ro còn đủ hấp dẫn.",
        risk="Nếu thị trường chung tiếp tục yếu, ngay cả setup đẹp cũng cần giảm size và kỳ vọng ngắn lại.",
    )

    return {
        "status": "ready" if rows else "missing",
        "summary": f"Execution context đã sẵn sàng cho {len(rows)} mã." if rows else "Chưa có execution context.",
        "posture": posture,
        "portfolio_risk": portfolio_risk,
        "rows": rows,
        "analyst_brief": brief,
    }
