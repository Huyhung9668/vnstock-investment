from __future__ import annotations

from datetime import datetime
from typing import Any

from services.insight_contracts import build_analyst_brief


DictStrAny = dict[str, Any]


def build_vnindex_vn30_derivatives_state(
    *,
    market_overview: dict[str, Any] | None,
    warnings: list[str] | None = None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    regime = _ensure_dict(normalized_market.get("regime"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    index_context = _ensure_dict(normalized_market.get("index_context"))

    vnindex_trend = _trend_from_regime(_text(regime.get("regime")))
    vn30_trend = _trend_from_return(_to_float(index_context.get("avg_return_3m")), fallback=vnindex_trend)
    positive_ratio = _to_float(breadth.get("positive_ratio"))
    ad_ratio = _to_float(breadth.get("advance_decline_ratio"))
    proxy_basis = _proxy_basis(positive_ratio=positive_ratio, ad_ratio=ad_ratio)
    futures_sentiment = "hedge_bias" if proxy_basis < 0 else "long_bias"
    regime_label = _regime_label(vn30_trend=vn30_trend, proxy_basis=proxy_basis)

    bullets = [
        f"VNINDEX hiện được xếp vào trạng thái {vnindex_trend}.",
        f"VN30 đang phản ánh trạng thái {vn30_trend}, dùng như lớp đối chiếu với nhóm trụ.",
        f"Basis proxy hiện quanh {proxy_basis:.2f}; đây là chỉ báo thay thế khi chưa có feed VN30F1M trực tiếp.",
        f"Tâm lý phái sinh suy luận hiện nghiêng về {futures_sentiment.replace('_', ' ')}.",
    ]
    if normalized_warnings:
        bullets.append("Do chưa có feed phái sinh đầy đủ, phần basis và sentiment đang được dùng theo chế độ proxy an toàn.")

    headline = f"VNINDEX và VN30 đang ở trạng thái {vnindex_trend}; lớp phái sinh hiện nghiêng về {futures_sentiment.replace('_', ' ')}."
    conclusion = (
        "Nếu VN30 giữ tốt hơn VNINDEX và basis proxy bớt âm, khả năng thị trường chuyển từ phòng thủ sang cân bằng sẽ cao hơn."
        if proxy_basis < 0
        else "Nếu VN30 duy trì khỏe hơn VNINDEX và basis proxy dương thêm, xác suất nhóm trụ dẫn sóng sẽ cao hơn."
    )

    return {
        "status": "ready" if normalized_market else "degraded",
        "headline": headline,
        "vnindex_trend": vnindex_trend,
        "vn30_trend": vn30_trend,
        "basis_proxy": round(proxy_basis, 2),
        "futures_sentiment": futures_sentiment,
        "regime": regime_label,
        "bullets": bullets,
        "source_timestamp": _text(normalized_market.get("generated_at")) or datetime.utcnow().isoformat(timespec="seconds"),
        "conclusion": conclusion,
        "analyst_brief": build_analyst_brief(
            insight=headline,
            evidence=bullets[:3],
            implication="Cần đọc VNINDEX, VN30 và lớp phái sinh như một chuỗi xác nhận thay vì tách rời từng chỉ báo.",
            action="Ưu tiên hành động khi chỉ số cơ sở, nhóm trụ và tín hiệu basis không còn mâu thuẫn nhau.",
            risk="Khi basis proxy còn âm sâu và độ rộng yếu, rủi ro hồi kỹ thuật rồi thất bại vẫn ở mức cao.",
        ),
    }


def _trend_from_regime(value: str) -> str:
    mapping = {"risk_on": "tăng có chọn lọc", "risk_off": "phòng thủ", "balanced": "cân bằng", "narrow_leadership": "phân hóa hẹp"}
    return mapping.get(value.strip().lower(), "trung tính")


def _trend_from_return(value: float | None, *, fallback: str) -> str:
    if value is None:
        return fallback
    if value > 0.03:
        return "tăng"
    if value < -0.03:
        return "yếu"
    return "đi ngang"


def _proxy_basis(*, positive_ratio: float | None, ad_ratio: float | None) -> float:
    ratio = positive_ratio if positive_ratio is not None else 0.5
    ad = ad_ratio if ad_ratio is not None else 1.0
    return round((ratio - 0.5) * 10 + (ad - 1.0) * 2, 2)


def _regime_label(*, vn30_trend: str, proxy_basis: float) -> str:
    if proxy_basis <= -1.0:
        return "hedge"
    if proxy_basis >= 1.0 and vn30_trend in {"tăng", "tăng có chọn lọc"}:
        return "trend"
    if "yếu" in vn30_trend:
        return "failed_breakout"
    return "mean_reversion"


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
