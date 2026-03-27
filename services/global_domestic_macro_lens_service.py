from __future__ import annotations

from datetime import datetime
from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_global_domestic_macro_lens(
    *,
    market_overview: dict[str, Any] | None,
    market_news_summary: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_news = dict(market_news_summary or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    regime = _ensure_dict(normalized_market.get("regime"))
    index_context = _ensure_dict(normalized_market.get("index_context"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    themes = _string_list(normalized_market.get("market_themes"))
    headline_digest = _string_list(normalized_news.get("headline_digest"))

    regime_name = _text(regime.get("regime")).lower() or "unknown"
    explanation = _text(regime.get("explanation"))
    avg_return_3m = _to_float(index_context.get("avg_return_3m"))
    positive_ratio = _to_float(breadth.get("positive_ratio"))

    macro_score = 0.0
    drivers: list[str] = []
    risk_flags: list[str] = []

    if regime_name == "risk_on":
        macro_score += 1.0
        drivers.append("Khẩu vị rủi ro tổng thể đang nghiêng sang hướng tích cực hơn.")
    elif regime_name == "risk_off":
        macro_score -= 1.0
        risk_flags.append("Bối cảnh chung vẫn mang màu sắc phòng thủ, chưa thuận lợi cho chiến lược mua lan tỏa.")

    if positive_ratio is not None:
        if positive_ratio >= 0.55:
            macro_score += 0.75
            drivers.append(f"Độ rộng thị trường đang cải thiện với tỷ lệ mã tăng khoảng {positive_ratio * 100:.2f}%.")
        elif positive_ratio <= 0.4:
            macro_score -= 0.75
            risk_flags.append(f"Độ rộng yếu với tỷ lệ mã tăng chỉ quanh {positive_ratio * 100:.2f}%.")

    if avg_return_3m is not None:
        if avg_return_3m > 0:
            macro_score += 0.5
            drivers.append(f"Xung lực trung hạn của rổ theo dõi vẫn dương khoảng {avg_return_3m * 100:.2f}%.")
        else:
            macro_score -= 0.5
            risk_flags.append(f"Xung lực trung hạn của rổ theo dõi còn âm khoảng {avg_return_3m * 100:.2f}%.")

    if explanation:
        drivers.append(explanation)
    drivers.extend(headline_digest[:3])

    if any("fx" in warning.lower() or "exchange" in warning.lower() for warning in normalized_warnings):
        risk_flags.append("Cần theo dõi thêm biến động tỷ giá vì đây là biến nhạy cảm với dòng vốn ngoại và nhóm vốn hóa lớn.")
    if any("rate limit" in warning.lower() for warning in normalized_warnings):
        risk_flags.append("Một phần feed ngoài thị trường có thể chưa đầy đủ nên lớp vĩ mô cần được đọc theo hướng phòng thủ hơn.")

    if macro_score >= 0.75:
        macro_regime = "risk_on"
    elif macro_score <= -0.75:
        macro_regime = "risk_off"
    else:
        macro_regime = "neutral"

    sector_impacts = _sector_impacts(macro_regime=macro_regime, themes=themes)
    narrative = _narrative(macro_regime=macro_regime, drivers=drivers, risk_flags=risk_flags)
    source_timestamp = _timestamp(normalized_market, normalized_news)

    return {
        "status": "ready" if normalized_market else "degraded",
        "macro_regime": macro_regime,
        "macro_score": round(macro_score, 2),
        "drivers": drivers[:5],
        "risk_flags": risk_flags[:5],
        "sector_impacts": sector_impacts,
        "source_timestamp": source_timestamp,
        "narrative": narrative,
        "analyst_brief": build_analyst_brief(
            insight=(
                "Lớp intermarket hiện nghiêng về tích cực có chọn lọc, nhưng vẫn cần nhìn đồng thời độ rộng và dòng tiền xác nhận."
                if macro_regime == "risk_on"
                else "Lớp intermarket hiện nghiêng về phòng thủ; nên ưu tiên quản trị rủi ro trước khi mở rộng vị thế."
                if macro_regime == "risk_off"
                else "Lớp intermarket đang ở trạng thái trung tính; thị trường cần thêm dữ kiện để xác nhận hướng đi rõ ràng hơn."
            ),
            evidence=drivers[:3] + risk_flags[:2],
            implication=narrative,
            action="Ưu tiên nhóm ít chịu áp lực định giá và chỉ giải ngân mạnh hơn khi độ rộng, dòng tiền và chỉ số đồng pha.",
            risk=(risk_flags[0] if risk_flags else "Thiếu feed liên thị trường trực tiếp nên kết luận nên được dùng như lớp định hướng, không phải tín hiệu đơn lẻ."),
        ),
    }


def _sector_impacts(*, macro_regime: str, themes: list[str]) -> list[DictStrAny]:
    if macro_regime == "risk_on":
        base = [
            {"sector": "Ngân hàng", "impact": "positive", "reason": "Khẩu vị rủi ro cải thiện thường hỗ trợ nhóm trụ và nhóm dẫn sóng thanh khoản."},
            {"sector": "Chứng khoán", "impact": "positive", "reason": "Môi trường giao dịch tích cực hơn thường kéo theo kỳ vọng cải thiện thanh khoản."},
        ]
    elif macro_regime == "risk_off":
        base = [
            {"sector": "Ngân hàng", "impact": "mixed", "reason": "Nhóm trụ có thể giữ nhịp chỉ số nhưng khó lan tỏa nếu độ rộng yếu."},
            {"sector": "Phòng thủ", "impact": "positive", "reason": "Dòng tiền có xu hướng tìm tới nhóm ổn định hơn khi rủi ro tăng lên."},
        ]
    else:
        base = [
            {"sector": "Ngân hàng", "impact": "mixed", "reason": "Đây vẫn là nhóm cần theo dõi để xác nhận dòng tiền dẫn dắt."},
            {"sector": "Chứng khoán", "impact": "mixed", "reason": "Nhóm nhạy với thanh khoản nên chỉ phù hợp khi thị trường xác nhận mạnh hơn."},
        ]
    if themes:
        base.append({"sector": "Theo theme", "impact": "mixed", "reason": f"Các theme đang nổi lên gồm: {', '.join(themes[:3])}."})
    return base[:4]


def _narrative(*, macro_regime: str, drivers: list[str], risk_flags: list[str]) -> str:
    lead = drivers[0] if drivers else "Chưa có đủ tín hiệu liên thị trường nổi trội"
    risk = risk_flags[0] if risk_flags else "rủi ro hiện tại chưa có cảnh báo nổi bật ngoài biến động giá"
    if macro_regime == "risk_on":
        return f"{lead} Điều đó cho phép nghiêng nhẹ về kịch bản tích cực, nhưng vẫn cần dòng tiền nội xác nhận để biến tín hiệu vĩ mô thành nhịp tăng bền của chứng khoán Việt Nam."
    if macro_regime == "risk_off":
        return f"{lead} Vì vậy, thị trường chứng khoán Việt Nam vẫn nên được nhìn dưới lăng kính phòng thủ; {risk.lower()}"
    return f"{lead} Tác động lên chứng khoán Việt Nam hiện mới ở mức trung tính, nên chiến lược phù hợp là quan sát thêm các nhóm dẫn dắt thay vì hành động rộng."


def _timestamp(market_overview: DictStrAny, market_news_summary: DictStrAny) -> str:
    for source in [market_overview, market_news_summary]:
        for key in ["generated_at", "timestamp", "as_of"]:
            value = _text(source.get(key))
            if value:
                return value
    return datetime.utcnow().isoformat(timespec="seconds")


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
