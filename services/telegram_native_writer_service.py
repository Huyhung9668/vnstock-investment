from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_telegram_native_brief(
    *,
    run_id: str,
    chief_analysis: dict[str, Any] | None,
    market_brain: dict[str, Any] | None,
    analysis_critic: dict[str, Any] | None,
    long_candidates: dict[str, Any] | None,
    entry_execution: dict[str, Any] | None,
) -> DictStrAny:
    analysis = dict(chief_analysis or {})
    brain = dict(market_brain or {})
    critic = dict(analysis_critic or {})
    long_payload = dict(long_candidates or {})
    execution = dict(entry_execution or {})

    sections = [dict(item) for item in (analysis.get("sections") or []) if isinstance(item, dict)]
    bias = _text(analysis.get("stance")) or "trung tính"
    confidence = _text(analysis.get("confidence")) or _text(brain.get("confidence_override")) or "chưa rõ"
    thesis = _text(brain.get("market_thesis")) or _text(analysis.get("summary"))
    priorities = [str(item).strip() for item in (brain.get("today_priorities") or []) if str(item).strip()]
    selected = [dict(item) for item in (long_payload.get("selected") or []) if isinstance(item, dict)]

    messages: list[str] = []
    messages.append(
        "\n".join([
            f"[1/5] Nhịp thị trường hôm nay",
            f"Cập nhật: {run_id}",
            "",
            thesis,
            f"Bias hiện tại: {bias} | Độ tin cậy: {confidence}",
            *( [""] + [f"- {item}" for item in priorities[:3]] if priorities else []),
        ]).strip()
    )

    macro_sections = _find_sections(sections, ["Vĩ Mô", "VNIndex", "Khối Ngoại", "Nội Tạng"])
    messages.append(_render_compact_message("[2/5] Bối cảnh vĩ mô, chỉ số và dòng tiền", macro_sections))

    sector_sections = _find_sections(sections, ["Sức Mạnh Ngành", "Tin Tức", "Kịch Bản"])
    messages.append(_render_compact_message("[3/5] Ngành, tin tức và kịch bản", sector_sections))

    top_lines = ["[4/5] Top cổ phiếu LONG đáng theo dõi", ""]
    if selected:
        for idx, item in enumerate(selected[:5], start=1):
            symbol = _text(item.get("symbol"))
            trigger = _text(item.get("trigger"))
            rr = _text(item.get("risk_reward"))
            note = _clean_sentence(_text(item.get("selection_note")))
            top_lines.extend([
                f"{idx}. {symbol}",
                f"- Vùng theo dõi: {trigger}",
                f"- RR tham chiếu: {rr}",
                f"- Ý chính: {note}",
            ])
    else:
        top_lines.append("Hiện chưa có đủ mã đạt chuẩn LONG để nâng thành kế hoạch hành động rõ ràng.")
    messages.append("\n".join(top_lines).strip())

    entry_lines = ["[5/5] Kế hoạch vào lệnh và quản trị rủi ro", ""]
    entries = [dict(item) for item in (execution.get("entries") or []) if isinstance(item, dict)]
    if entries:
        for item in entries[:3]:
            symbol = _text(item.get("symbol"))
            zone = _text(item.get("entry_zone"))
            stop_note = _text(item.get("stop_note"))
            take_profit = _text(item.get("take_profit_note"))
            entry_lines.extend([
                f"- {symbol}: vùng mua {zone}",
                f"  • {stop_note}",
                f"  • {take_profit}",
            ])
    else:
        entry_lines.append("Chưa kích hoạt kế hoạch vào lệnh mới; ưu tiên giữ watchlist và chờ xác nhận tốt hơn.")
    critic_issues = [str(item).strip() for item in (critic.get("issues") or []) if str(item).strip()]
    if critic_issues:
        entry_lines.extend(["", "Lưu ý:", f"- {critic_issues[0]}"])
    messages.append("\n".join(entry_lines).strip())

    return {"status": "ready", "messages": messages}


def _find_sections(sections: list[DictStrAny], keywords: list[str]) -> list[DictStrAny]:
    found: list[DictStrAny] = []
    for keyword in keywords:
        for section in sections:
            title = _text(section.get("title"))
            if keyword.lower() in title.lower() and section not in found:
                found.append(section)
                break
    return found


def _render_compact_message(header: str, sections: list[DictStrAny]) -> str:
    lines = [header, ""]
    for section in sections:
        title = _text(section.get("title"))
        paragraphs = _section_points(section)
        if not title or not paragraphs:
            continue
        lines.append(f"{title}:")
        lines.extend([f"- {item}" for item in paragraphs[:3]])
        lines.append("")
    return "\n".join(lines).strip()


def _section_points(section: DictStrAny) -> list[str]:
    raw = [str(item).strip() for item in (section.get("paragraphs") or []) if str(item).strip()]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        normalized = _normalize_line(item)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned


def _normalize_line(text: str) -> str:
    line = " ".join(text.split())
    if not line:
        return ""
    bad_prefixes = [
        "Cơ sở chính hiện tại là ",
        "Điểm cần thận trọng là ",
    ]
    for prefix in bad_prefixes:
        if line.startswith(prefix):
            line = line[len(prefix):]
    line = line.replace("UNKNOWN", "chưa phân loại rõ")
    line = line.replace("negative", "tiêu cực")
    line = line.replace("positive", "tích cực")
    line = line.replace("buy_on_pullback", "mua khi điều chỉnh")
    line = line.replace("basis proxy", "basis suy luận")
    line = line.replace("hedge bias", "thiên về phòng thủ")
    if ";" in line and len(line) > 180:
        line = "; ".join(part.strip() for part in line.split(";")[:2] if part.strip())
    return _clean_sentence(line.rstrip(".")) + "."


def _clean_sentence(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
