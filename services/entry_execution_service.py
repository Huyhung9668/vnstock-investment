from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_entry_execution_plan(*, selected_candidates: list[dict[str, Any]] | None) -> DictStrAny:
    candidates = [dict(item) for item in (selected_candidates or []) if isinstance(item, dict)]
    entries: list[DictStrAny] = []

    for item in candidates[:5]:
        symbol = str(item.get("symbol", "")).strip().upper()
        trigger = str(item.get("trigger", "")).strip() or "chờ vùng mua rõ hơn"
        invalidation = str(item.get("invalidation", "")).strip() or "gãy cấu trúc hỗ trợ gần nhất"
        risk_reward = item.get("risk_reward")
        entries.append(
            {
                "symbol": symbol,
                "entry_zone": trigger,
                "allocation_plan": [
                    "30% vị thế thăm dò khi giá về đúng vùng mua hoặc giữ được nền hỗ trợ.",
                    "30% tiếp theo khi giá xác nhận hồi phục hoặc bật lên với thanh khoản ổn định.",
                    "40% còn lại chỉ thêm khi xu hướng ngắn hạn được xác nhận rõ hơn.",
                ],
                "stop_note": f"Dừng lại nếu {invalidation.rstrip('.').lower()}.",
                "take_profit_note": (
                    f"Chốt lời từng phần khi tỷ lệ lợi nhuận/rủi ro tiến gần mức {risk_reward}."
                    if risk_reward not in {None, '', 'n/a'} else "Chốt lời từng phần khi giá tiệm cận vùng cản gần nhất."
                ),
            }
        )

    return {
        "status": "ready" if entries else "missing",
        "portfolio_posture": "Giải ngân chậm, ưu tiên xác nhận rồi mới gia tăng.",
        "global_rules": [
            "Không mua đuổi khi cổ phiếu đã tăng nóng rời xa vùng nền.",
            "Chỉ nâng tỷ trọng khi thị trường chung và cổ phiếu cùng xác nhận tín hiệu tích cực.",
            "Mỗi lệnh đều phải có điểm vô hiệu rõ ràng trước khi vào vị thế.",
        ],
        "entries": entries,
    }
