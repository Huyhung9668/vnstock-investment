from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_market_brain(
    *,
    market_synthesis: dict[str, Any] | None,
    chief_analysis: dict[str, Any] | None,
    long_candidates: dict[str, Any] | None,
) -> DictStrAny:
    synthesis = dict(market_synthesis or {})
    analysis = dict(chief_analysis or {})
    candidates = dict(long_candidates or {})

    market_score = _ensure_dict(synthesis.get("market_score"))
    score = _to_float(market_score.get("score")) or 50.0
    bias = _text(market_score.get("bias")).lower() or "neutral"
    focus_rows = [dict(item) for item in (synthesis.get("top_stock_focus") or []) if isinstance(item, dict)]
    selected = [dict(item) for item in (candidates.get("selected") or []) if isinstance(item, dict)]

    thesis = _build_thesis(score=score, bias=bias, focus_rows=focus_rows)
    today_priorities = _priorities(synthesis=synthesis, selected=selected)
    writing_agenda = _agenda(synthesis=synthesis, selected=selected)
    tone = "decisive" if score >= 65 else "defensive" if score <= 40 else "balanced"

    return {
        "status": "ready",
        "market_thesis": thesis,
        "today_priorities": today_priorities,
        "writing_agenda": writing_agenda,
        "tone": tone,
        "lead_symbol": _text(focus_rows[0].get("symbol")) if focus_rows else "watchlist",
        "confidence_override": analysis.get("confidence") or synthesis.get("confidence") or "trung bình",
    }


def _build_thesis(*, score: float, bias: str, focus_rows: list[DictStrAny]) -> str:
    lead_symbol = _text(focus_rows[0].get("symbol")) if focus_rows else "watchlist"
    if score <= 40:
        return f"Trục chính hôm nay là phòng thủ và chọn lọc rất kỹ; chỉ giữ {lead_symbol} như mã quan sát ưu tiên thay vì mở rộng giải ngân."
    if score >= 65:
        return f"Trục chính hôm nay là tấn công có chọn lọc; có thể ưu tiên {lead_symbol} nếu thị trường xác nhận thêm độ lan tỏa."
    return f"Trục chính hôm nay là quan sát phản ứng giá và dòng tiền; {lead_symbol} là điểm kiểm tra quan trọng nhất trước khi nâng mức cam kết vốn."


def _priorities(*, synthesis: DictStrAny, selected: list[DictStrAny]) -> list[str]:
    priorities: list[str] = []
    market_internals = _ensure_dict(synthesis.get("market_internals"))
    derivatives = _ensure_dict(synthesis.get("derivatives_state"))
    if market_internals:
        priorities.append(_text(market_internals.get("explanation")))
    if derivatives:
        priorities.append(_text(derivatives.get("conclusion")))
    if selected:
        symbol = _text(selected[0].get("symbol"))
        trigger = _text(selected[0].get("trigger"))
        priorities.append(f"Theo dõi sát {symbol} quanh vùng {trigger} để kiểm tra xem dòng tiền có thực sự chấp nhận giá hay không.")
    return [item for item in priorities if item][:3]


def _agenda(*, synthesis: DictStrAny, selected: list[DictStrAny]) -> list[str]:
    agenda = [
        "Mở bài bằng thesis quan trọng nhất của ngày.",
        "Giải thích vì sao thị trường đang ở trạng thái hiện tại bằng độ rộng, dòng tiền và cấu trúc chỉ số.",
        "Chỉ nói dài ở những phần có tín hiệu thật; phần thiếu data phải nói ngắn và rõ là proxy.",
    ]
    if selected:
        agenda.append("Kết luận bằng một kế hoạch hành động hẹp, có trigger và invalidation rõ ràng cho nhóm top picks.")
    return agenda[:4]


def _ensure_dict(value: Any) -> DictStrAny:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
