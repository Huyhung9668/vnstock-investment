from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_scenario_engine(
    *,
    market_overview: dict[str, Any] | None,
    long_candidates: dict[str, Any] | None = None,
    sector_strength: dict[str, Any] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_candidates = dict(long_candidates or {})
    normalized_sector = dict(sector_strength or {})
    breadth = _ensure_dict(normalized_market.get("breadth"))
    positive_ratio = _to_float(breadth.get("positive_ratio")) or 0.0
    selected = [dict(item) for item in (normalized_candidates.get("selected") or []) if isinstance(item, dict)]
    leading = [dict(item) for item in (normalized_sector.get("leading") or []) if isinstance(item, dict)]

    positive = {
        "name": "positive",
        "trigger_conditions": ["Độ rộng mở rộng lên trên 50% mã tăng.", "Nhóm dẫn dắt giữ thanh khoản tốt và xuất hiện thêm nhóm improving nhập cuộc."],
        "affected_sectors": [item.get("sector") for item in leading[:3] if item.get("sector")],
        "tactical_action": "Có thể tăng dần tỷ trọng ở các mã LONG khỏe khi giá xác nhận đúng vùng mua.",
        "invalidation": "Kịch bản này mất hiệu lực nếu chỉ số tăng nhưng độ rộng không cải thiện hoặc dòng tiền co hẹp trở lại.",
    }
    base = {
        "name": "base",
        "trigger_conditions": ["Thị trường dao động trong biên hẹp và độ rộng chỉ cải thiện vừa phải.", "Nhóm trụ giữ nhịp nhưng chưa tạo lan tỏa sang phần còn lại của thị trường."],
        "affected_sectors": [item.get("symbol") for item in selected[:3] if item.get("symbol")],
        "tactical_action": "Giải ngân chậm, ưu tiên vị thế thăm dò và chờ xác nhận bổ sung trước khi gia tăng.",
        "invalidation": "Kịch bản cơ sở bị thay thế nếu thị trường bứt hẳn lên với breadth mạnh hoặc gãy hỗ trợ đồng loạt.",
    }
    negative = {
        "name": "negative",
        "trigger_conditions": ["Độ rộng tiếp tục dưới 35% mã tăng.", "Thanh khoản co hẹp hoặc chỉ tập trung vào một số mã trụ phòng thủ."],
        "affected_sectors": ["Đầu cơ", "Beta cao", "Nhóm không có dòng tiền xác nhận"],
        "tactical_action": "Giảm nhịp giải ngân, ưu tiên bảo toàn vốn và chỉ giữ lại các mã còn cấu trúc tốt nhất.",
        "invalidation": "Kịch bản tiêu cực bị phủ nhận khi độ rộng và nhóm dẫn dắt cùng cải thiện trở lại.",
    }
    base_case = "positive" if positive_ratio >= 0.55 else "negative" if positive_ratio <= 0.35 else "base"

    return {
        "status": "ready",
        "base_case": base_case,
        "scenarios": [positive, base, negative],
        "analyst_brief": build_analyst_brief(
            insight=f"Kịch bản cơ sở hiện tại nghiêng về {base_case}, vì vậy kế hoạch hành động nên được gắn với điều kiện kích hoạt rõ ràng.",
            evidence=positive["trigger_conditions"][:1] + base["trigger_conditions"][:1] + negative["trigger_conditions"][:1],
            implication="Thị trường nên được đọc theo kịch bản và điều kiện xác nhận, thay vì cố chốt một nhận định cứng cho mọi hoàn cảnh.",
            action="Chuẩn bị sẵn trigger cho từng kịch bản để tránh phản ứng cảm tính khi thị trường biến động nhanh.",
            risk="Nếu không xác định trước điều kiện vô hiệu, rất dễ rơi vào trạng thái giữ lệnh sai vì kỳ vọng chủ quan.",
        ),
    }


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
