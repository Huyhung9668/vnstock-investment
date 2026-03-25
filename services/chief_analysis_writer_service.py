from __future__ import annotations

from datetime import datetime
from typing import Any


DictStrAny = dict[str, Any]


def build_chief_analysis(
    *,
    synthesis: dict[str, Any],
    generated_at: str | None = None,
    ai_analysis: dict[str, Any] | None = None,
    skill_pipeline: dict[str, Any] | None = None,
) -> DictStrAny:
    normalized_synthesis = dict(synthesis or {})
    normalized_ai = dict(ai_analysis or {})
    normalized_pipeline = dict(skill_pipeline or {})
    stages = _ensure_dict(normalized_pipeline.get("stages"))
    effective_generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    macro_brief = _brief_from_stage(stages, "macro_context")
    news_brief = _brief_from_stage(stages, "news_context")
    flow_brief = _brief_from_stage(stages, "flow_of_funds")
    scanner_brief = _brief_from_stage(stages, "stock_scanner")
    technical_brief = _brief_from_stage(stages, "technical_profiler")
    risk_brief = _brief_from_stage(stages, "risk_engine")
    execution_brief = _brief_from_stage(stages, "execution_context")
    portfolio_brief = _brief_from_stage(stages, "portfolio_auditor")

    focus_rows = _normalize_focus_rows(normalized_synthesis.get("top_stock_focus"))
    title = _text(normalized_ai.get("headline")) or "Nhận Định Thị Trường & Kế Hoạch Hành Động"
    summary = _text(normalized_ai.get("market_story")) or _build_summary(normalized_synthesis, macro_brief, scanner_brief, focus_rows)

    sections = [
        {"title": "Tóm Tắt Điều Hành", "paragraphs": _executive_paragraphs(normalized_synthesis, focus_rows, portfolio_brief)},
        {"title": "Bối Cảnh Vĩ Mô & Tâm Lý", "paragraphs": _brief_section(macro_brief, fallback="Chưa có thêm lớp bối cảnh vĩ mô đủ mạnh ngoài tín hiệu thị trường chung.")},
        {"title": "Tin Tức & Catalyst", "paragraphs": _brief_section(news_brief, fallback="Hiện chưa có lớp tin tức đủ nổi bật để tạo lợi thế diễn giải riêng cho nhóm mã theo dõi.")},
        {"title": "Cấu Trúc Thị Trường & Dòng Tiền", "paragraphs": _merge_section_paragraphs(_brief_section(flow_brief), _market_structure_paragraphs(normalized_synthesis))},
        {"title": "5 Mã Cần Theo Dõi", "paragraphs": _focus_paragraphs(focus_rows, scanner_brief, technical_brief), "bullets": _focus_bullets(focus_rows)},
        {"title": "Kế Hoạch Hành Động", "paragraphs": _merge_section_paragraphs(_brief_section(execution_brief), _brief_section(portfolio_brief))},
        {"title": "Rủi Ro Cần Theo Dõi", "paragraphs": _brief_section(risk_brief, fallback="Rủi ro lớn nhất hiện tại là hành động quá sớm khi thị trường vẫn chưa cho độ lan tỏa đủ mạnh.")},
        {"title": "Kết Luận", "paragraphs": [_closing_paragraph(normalized_synthesis, focus_rows, execution_brief)]},
    ]

    return {
        "title": title,
        "update_line": f"Cập nhật: {effective_generated_at}",
        "summary": summary,
        "stance": _localized_stance(normalized_synthesis.get("stance")),
        "confidence": _localized_confidence(normalized_synthesis.get("confidence")),
        "sections": sections,
    }


def _build_summary(synthesis: DictStrAny, macro_brief: DictStrAny, scanner_brief: DictStrAny, focus_rows: list[DictStrAny]) -> str:
    lead_symbol = _text(focus_rows[0].get("symbol")) if focus_rows else "nhóm cổ phiếu ưu tiên"
    macro_insight = _text(macro_brief.get("insight"))
    scanner_insight = _text(scanner_brief.get("insight"))
    if macro_insight and scanner_insight:
        return f"{macro_insight} {scanner_insight} Trong bối cảnh đó, {lead_symbol} là điểm theo dõi nổi bật nhất hiện tại."
    regime = _localized_regime(_infer_regime_label(synthesis))
    confidence = _localized_confidence(synthesis.get("confidence"))
    return f"Thị trường hiện nghiêng về trạng thái {regime}. Trong bối cảnh đó, {lead_symbol} là điểm theo dõi nổi bật nhất, nhưng cách tiếp cận phù hợp vẫn là chọn lọc kỹ và giữ kỷ luật vì độ tin cậy dữ liệu đang ở mức {confidence}."


def _executive_paragraphs(synthesis: DictStrAny, focus_rows: list[DictStrAny], portfolio_brief: DictStrAny) -> list[str]:
    regime = _localized_regime(_infer_regime_label(synthesis))
    confidence = _localized_confidence(synthesis.get("confidence"))
    stance = _localized_stance(synthesis.get("stance"))
    lead = _text(focus_rows[0].get("symbol")) if focus_rows else "mã dẫn đầu"
    paragraphs = [
        f"Bức tranh tổng thể cho thấy thị trường đang ở trạng thái {regime}, nên ưu tiên lúc này không phải là mở rộng vị thế bằng mọi giá mà là giữ nhịp quan sát có chọn lọc. Khi trạng thái chung chưa thật sự thuận lợi, nhà đầu tư nên đặt trọng tâm vào độ rộng, dòng tiền và chất lượng điểm vào hơn là kỳ vọng vào một nhịp bứt phá lan tỏa toàn thị trường.",
        f"Với góc nhìn thực thi, chiến lược hợp lý hiện tại là {stance}. Mức độ tin cậy của bộ tổng hợp đang ở mức {confidence}, đủ để xây watchlist hành động và chuẩn bị kịch bản, nhưng chưa phù hợp để hành động thiếu chọn lọc.",
        f"Trong nhóm cổ phiếu nổi bật, {lead} đang là mã đáng chú ý nhất vì hội tụ được cả luận điểm theo dõi lẫn mức giá hành động tương đối rõ. Tuy nhiên, ngay cả với mã dẫn đầu, quyết định giải ngân vẫn nên gắn với phản ứng giá thực tế thay vì đi trước xác nhận.",
    ]
    paragraphs.extend(_brief_tail(portfolio_brief))
    return paragraphs[:4]


def _market_structure_paragraphs(synthesis: DictStrAny) -> list[str]:
    bullets = _normalize_string_list(synthesis.get("market_state"))
    positive_ratio = _extract_named_float(bullets, "positive_ratio")
    ad_ratio = _extract_named_float(bullets, "advance/decline_ratio")
    sentences: list[str] = []
    if positive_ratio is not None:
        if positive_ratio < 0.35:
            sentences.append(f"Độ lan tỏa hiện rất hẹp khi chỉ khoảng {_format_pct(positive_ratio)} số mã trong tập theo dõi còn giữ được sắc xanh")
        elif positive_ratio < 0.55:
            sentences.append(f"Độ rộng thị trường đang phân hóa, với khoảng {_format_pct(positive_ratio)} số mã tăng giá")
        else:
            sentences.append(f"Độ rộng đã cải thiện lên khoảng {_format_pct(positive_ratio)} số mã tăng giá")
    if ad_ratio is not None:
        if ad_ratio < 0.5:
            sentences.append("bên giảm giá vẫn áp đảo rõ rệt so với bên tăng giá")
        elif ad_ratio < 1:
            sentences.append("số mã giảm vẫn nhỉnh hơn số mã tăng, cho thấy xu hướng chưa thật sự chắc")
        else:
            sentences.append("số mã tăng đã cân bằng hoặc vượt số mã giảm")
    if not sentences:
        return ["Về cấu trúc thị trường, tín hiệu hiện tại vẫn nghiêng về phân hóa và cần thêm xác nhận trước khi nâng mức hành động."]
    return ["Các chỉ báo nội tại cho thấy " + "; ".join(sentences) + "."]


def _focus_paragraphs(focus_rows: list[DictStrAny], scanner_brief: DictStrAny, technical_brief: DictStrAny) -> list[str]:
    if not focus_rows:
        return ["Hiện chưa hình thành được danh sách cơ hội đủ rõ để nâng lên thành watchlist hành động."]
    lead = focus_rows[0]
    lead_symbol = _text(lead.get("symbol"))
    thesis = _humanize_thesis(_text(lead.get("thesis"))).lower()
    trigger = _text(lead.get("trigger"))
    rr = _text(lead.get("risk_reward"))
    first = f"Trong nhóm cổ phiếu ưu tiên, {lead_symbol} đang nổi bật nhất. Luận điểm chính xoay quanh việc {thesis}"
    if trigger and trigger.lower() != "wait":
        first += f", với vùng kích hoạt đáng chú ý quanh {trigger}"
    if rr and rr.lower() != "n/a":
        first += f" và tỷ lệ lợi nhuận/rủi ro tham chiếu khoảng {rr}"
    first += "."
    others = [row.get("symbol") for row in focus_rows[1:5] if _text(row.get("symbol"))]
    second = f"Các mã còn lại trong top ưu tiên gồm {', '.join(str(item) for item in others)}. Đây là nhóm phù hợp để theo dõi song song, nhưng nên ưu tiên mã có phản ứng giá tốt hơn mặt bằng chung trong phiên." if others else "Danh sách ưu tiên hiện còn khá hẹp, nên cần tập trung vào ít mã nhưng theo dõi đủ sâu."
    tail = _brief_tail(scanner_brief) + _brief_tail(technical_brief)
    return [first, second, *tail][:4]


def _closing_paragraph(synthesis: DictStrAny, focus_rows: list[DictStrAny], execution_brief: DictStrAny) -> str:
    regime = _localized_regime(_infer_regime_label(synthesis))
    stance = _localized_stance(synthesis.get("stance"))
    confidence = _localized_confidence(synthesis.get("confidence"))
    lead_symbol = _text(focus_rows[0].get("symbol")) if focus_rows else "nhóm cổ phiếu ưu tiên"
    extra = _text(execution_brief.get("action"))
    sentence = f"Tổng kết lại, thị trường đang ở trạng thái {regime}, nên cách tiếp cận phù hợp vẫn là {stance}. {lead_symbol} là điểm theo dõi nổi bật nhất trong nhóm ưu tiên, nhưng việc hành động chỉ nên diễn ra khi cấu trúc giá xác nhận rõ ràng. Trong bối cảnh độ tin cậy đang ở mức {confidence}, kỷ luật giao dịch quan trọng hơn sự hưng phấn ngắn hạn."
    if extra:
        sentence += f" {extra}"
    return sentence


def _brief_section(brief: DictStrAny, fallback: str | None = None) -> list[str]:
    paragraphs: list[str] = []
    insight = _text(brief.get("insight"))
    implication = _text(brief.get("implication"))
    action = _text(brief.get("action"))
    risk = _text(brief.get("risk"))
    evidence = [str(item).strip() for item in brief.get("evidence", []) if str(item).strip()] if isinstance(brief.get("evidence"), list) else []
    if insight:
        paragraphs.append(insight)
    if evidence:
        paragraphs.append("Cơ sở chính hiện tại là " + "; ".join(evidence[:3]).rstrip(".") + ".")
    if implication:
        paragraphs.append(implication)
    if action:
        paragraphs.append(action)
    if risk:
        paragraphs.append("Điểm cần thận trọng là " + risk[0].lower() + risk[1:] if len(risk) > 1 else risk)
    return paragraphs or ([fallback] if fallback else [])


def _brief_tail(brief: DictStrAny) -> list[str]:
    implication = _text(brief.get("implication"))
    action = _text(brief.get("action"))
    parts = [part for part in [implication, action] if part]
    return parts[:1]


def _merge_section_paragraphs(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            text = str(item).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def _focus_bullets(focus_rows: list[DictStrAny]) -> list[str]:
    bullets: list[str] = []
    for item in focus_rows[:5]:
        symbol = _text(item.get("symbol"))
        thesis = _humanize_thesis(_text(item.get("thesis")))
        trigger = _text(item.get("trigger"))
        risk_reward = _text(item.get("risk_reward"))
        if not symbol:
            continue
        line = f"{symbol}: {thesis}"
        if trigger and trigger.lower() != "wait":
            line += f" | Vùng theo dõi: {trigger}"
        if risk_reward and risk_reward.lower() != "n/a":
            line += f" | RR tham chiếu: {risk_reward}"
        bullets.append(line)
    return bullets


def _brief_from_stage(stages: DictStrAny, stage_name: str) -> DictStrAny:
    stage = _ensure_dict(stages.get(stage_name))
    brief = stage.get("analyst_brief")
    return dict(brief) if isinstance(brief, dict) else {}


def _normalize_focus_rows(payload: Any) -> list[DictStrAny]:
    if not isinstance(payload, list):
        return []
    return [dict(item) for item in payload if isinstance(item, dict)]


def _extract_named_float(lines: list[str], token: str) -> float | None:
    token_lower = token.lower()
    for line in lines:
        lower = str(line).lower()
        if token_lower not in lower or "=" not in lower:
            continue
        after = lower.split(token_lower, 1)[1].split("=", 1)[1].strip().split()[0].strip(".,;:")
        try:
            return float(after)
        except ValueError:
            continue
    return None


def _ensure_dict(value: Any) -> DictStrAny:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _humanize_thesis(text: str) -> str:
    cleaned = _clean_sentence(text)
    replacements = {
        "downtrend": "xu h??ng gi?m",
        "uptrend": "xu h??ng t?ng",
        "strong": "t?ch c?c",
        "negative": "ti?u c?c",
        "buy_on_pullback": "mua khi ?i?u ch?nh",
        "breakout_or_wait": "ch? ?i?m b?t ph?",
        "avoid_or_wait": "?u ti?n quan s?t",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = cleaned.replace('. ', '; ')
    return cleaned


def _clean_sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _localized_regime(value: Any) -> str:
    mapping = {"risk_on": "tích cực", "risk_off": "thận trọng", "balanced": "cân bằng", "narrow_leadership": "phân hóa hẹp", "unknown": "chưa rõ xu hướng"}
    text = (_text(value) or "unknown").lower()
    return mapping.get(text, text)


def _localized_stance(value: Any) -> str:
    mapping = {"selective offense": "tấn công có chọn lọc", "defensive": "phòng thủ chủ động", "caution": "thận trọng cao", "neutral": "trung tính", "unknown": "trung tính"}
    text = (_text(value) or "unknown").lower()
    return mapping.get(text, text)


def _localized_confidence(value: Any) -> str:
    mapping = {"high": "cao", "medium_high": "khá cao", "medium": "trung bình", "low": "thấp", "unknown": "chưa rõ"}
    text = (_text(value) or "unknown").lower()
    return mapping.get(text, text)


def _infer_regime_label(synthesis: DictStrAny) -> str:
    conclusion = _text(synthesis.get("conclusion")).lower()
    for label in ("risk_off", "risk_on", "balanced", "narrow_leadership"):
        if label in conclusion:
            return label
    stance = _text(synthesis.get("stance")).lower()
    if "defensive" in stance or "caution" in stance:
        return "risk_off"
    if "offense" in stance:
        return "risk_on"
    return "balanced"

