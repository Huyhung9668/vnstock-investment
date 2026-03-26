from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_vnindex_context(*, market_overview: dict[str, Any] | None) -> DictStrAny:
    overview = dict(market_overview or {})
    breadth = _ensure_dict(overview.get("breadth"))
    regime = _ensure_dict(overview.get("regime"))
    index_context = _ensure_dict(overview.get("index_context"))
    liquidity = _ensure_dict(overview.get("liquidity_concentration"))
    sectors = [dict(item) for item in (overview.get("sector_rotation") or []) if isinstance(item, dict)]

    advancers = _to_int(breadth.get("advancers"))
    decliners = _to_int(breadth.get("decliners"))
    unchanged = _to_int(breadth.get("unchanged"))
    total = _to_int(breadth.get("total_symbols"))
    positive_ratio = _to_float(breadth.get("positive_ratio"))
    ad_ratio = _to_float(breadth.get("advance_decline_ratio"))
    avg_return_3m = _to_float(index_context.get("avg_return_3m"))
    median_return_3m = _to_float(index_context.get("median_return_3m"))
    avg_volume = _to_float(index_context.get("avg_volume"))
    liquidity_share = _to_float(liquidity.get("top_n_liquidity_share"))
    top_liquidity_symbols = [str(item.get("symbol", "")).strip().upper() for item in (liquidity.get("top_symbols") or []) if str(item.get("symbol", "")).strip()]

    leading_sectors = [row for row in sectors if str(row.get("rotation_label", "")).strip().lower() == "leading"]
    lagging_sectors = [row for row in sectors if str(row.get("rotation_label", "")).strip().lower() == "lagging"]

    headline = _build_headline(regime=regime, positive_ratio=positive_ratio, ad_ratio=ad_ratio, avg_return_3m=avg_return_3m)
    metrics = {
        "proxy_index": str(index_context.get("proxy_index", "universe_equal_weight_proxy")).strip(),
        "regime": str(regime.get("regime", "unknown")).strip(),
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "total_symbols": total,
        "positive_ratio": positive_ratio,
        "advance_decline_ratio": ad_ratio,
        "avg_return_3m": avg_return_3m,
        "median_return_3m": median_return_3m,
        "avg_volume": avg_volume,
        "top_n_liquidity_share": liquidity_share,
    }

    bullets = [
        f"Độ rộng hiện tại: {advancers} mã tăng / {decliners} mã giảm / {unchanged} mã đi ngang trên tổng {total} mã theo dõi."
        if total > 0 else "Chưa đủ dữ liệu độ rộng để mô tả thị trường.",
        f"Tỷ lệ mã tăng chỉ đạt {_fmt_pct(positive_ratio, scale=100)}; tỷ lệ tăng/giảm ở mức {_fmt_num(ad_ratio, 2)}."
        if positive_ratio is not None or ad_ratio is not None else "Chưa đủ dữ liệu nội tại để tính positive ratio và advance/decline.",
        f"Xung lực trung hạn của tập theo dõi đang ở mức {_fmt_pct(avg_return_3m, scale=100)}; trung vị 3 tháng là {_fmt_pct(median_return_3m, scale=100)}."
        if avg_return_3m is not None else "Chưa tính được xung lực trung hạn của tập theo dõi.",
        f"Thanh khoản tập trung mạnh vào nhóm dẫn dắt, với { _fmt_pct(liquidity_share, scale=100) } giá trị dồn vào top thanh khoản: {', '.join(top_liquidity_symbols[:3])}."
        if liquidity_share is not None and top_liquidity_symbols else "Chưa xác định được nhóm dẫn dắt về thanh khoản.",
    ]
    bullets = [item for item in bullets if item]

    sector_bullets: list[str] = []
    if leading_sectors:
        sector_bullets.append(
            "Nhóm dẫn dắt tương đối: " + ", ".join(
                f"{_sector_name(item)} ({_fmt_pct(_to_float(item.get('avg_return_3m')), scale=100)})" for item in leading_sectors[:3]
            ) + "."
        )
    if lagging_sectors:
        sector_bullets.append(
            "Nhóm yếu hơn mặt bằng: " + ", ".join(
                f"{_sector_name(item)} ({_fmt_pct(_to_float(item.get('avg_return_3m')), scale=100)})" for item in lagging_sectors[:3]
            ) + "."
        )

    action_bias = _build_action_bias(str(regime.get("regime", "unknown")).strip(), positive_ratio, ad_ratio)
    risk_note = _build_risk_note(positive_ratio=positive_ratio, liquidity_share=liquidity_share)

    return {
        "status": "ready" if overview else "missing",
        "headline": headline,
        "metrics": metrics,
        "bullets": bullets,
        "sector_bullets": sector_bullets,
        "action_bias": action_bias,
        "risk_note": risk_note,
    }


def _build_headline(*, regime: DictStrAny, positive_ratio: float | None, ad_ratio: float | None, avg_return_3m: float | None) -> str:
    regime_name = str(regime.get("regime", "unknown")).strip().lower()
    if regime_name == "risk_off":
        return "VNINDEX đang ở nhịp phòng thủ; bên bán vẫn chiếm ưu thế và dòng tiền chưa mở rộng đủ mạnh."
    if regime_name == "risk_on":
        return "VNINDEX đang ở trạng thái thuận lợi hơn cho bên mua; độ rộng và dòng tiền cùng cải thiện."
    if positive_ratio is not None and positive_ratio < 0.3:
        return "VNINDEX đang phân hóa yếu; số mã giữ được sắc xanh còn quá ít để ủng hộ mua lan tỏa."
    if avg_return_3m is not None and avg_return_3m < 0:
        return "VNINDEX đang ở vùng cân bằng yếu; xung lực trung hạn của tập theo dõi vẫn chưa quay lại tích cực."
    return "VNINDEX đang trong giai đoạn giằng co; cần theo dõi thêm độ rộng và thanh khoản để xác nhận hướng đi kế tiếp."


def _build_action_bias(regime: str, positive_ratio: float | None, ad_ratio: float | None) -> str:
    regime_key = str(regime).strip().lower()
    if regime_key == "risk_on" and (positive_ratio or 0) >= 0.55:
        return "Có thể tăng mức chủ động với các setup LONG mạnh, nhưng vẫn tránh mua đuổi khi giá đã rời nền."
    if regime_key == "risk_off" or (positive_ratio or 0) <= 0.3 or (ad_ratio or 0) < 0.8:
        return "Ưu tiên LONG có chọn lọc, giải ngân chậm và chỉ tập trung vào vài mã khỏe nhất."
    return "Giữ trạng thái trung tính, ưu tiên quan sát phản ứng giá tại các vùng hỗ trợ và cản ngắn hạn."


def _build_risk_note(*, positive_ratio: float | None, liquidity_share: float | None) -> str:
    if positive_ratio is not None and positive_ratio <= 0.2:
        return "Độ rộng quá hẹp là rủi ro lớn nhất: chỉ cần nhóm dẫn dắt hụt lực, toàn bộ nhịp hồi có thể mất đà rất nhanh."
    if liquidity_share is not None and liquidity_share >= 0.85:
        return "Dòng tiền tập trung quá mạnh vào một cụm nhỏ khiến xu hướng chung thiếu nền tảng lan tỏa."
    return "Rủi ro nằm ở khả năng thị trường chỉ hồi kỹ thuật nhưng chưa tạo được nền tăng bền vững."


def _sector_name(item: DictStrAny) -> str:
    name = str(item.get("sector", "UNKNOWN")).strip().upper()
    return "Chưa phân loại" if name == "UNKNOWN" else name.title()


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _fmt_pct(value: float | None, scale: float = 1.0) -> str:
    if value is None:
        return "n/a"
    return f"{value * scale:.2f}%"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"
