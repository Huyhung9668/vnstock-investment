from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)
MAX_TELEGRAM_TEXT_LENGTH = 3500


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled

    def _build_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str) -> bool:
        return self.send_messages([text])

    def send_messages(self, messages: list[str]) -> bool:
        if not self.enabled:
            logger.info("Telegram notifier disabled.")
            return False
        try:
            normalized = [_plain_text_message(message) for message in messages if str(message).strip()]
            if not normalized:
                return False
            total_chunks = 0
            for message in normalized:
                chunks = _chunk_message(message, max_length=MAX_TELEGRAM_TEXT_LENGTH)
                if not chunks:
                    continue
                total_chunks += len(chunks)
                for chunk in chunks:
                    response = self._post_message(text=chunk, parse_mode=None)
                    if response.status_code != 200:
                        logger.warning("Telegram plain text send failed: %s", response.text)
                        return False
            logger.info("Telegram message sent successfully in %s chunk(s).", total_chunks)
            return True
        except Exception as exc:
            logger.warning("Telegram error: %s", exc)
            return False

    def _post_message(self, *, text: str, parse_mode: str | None) -> requests.Response:
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return requests.post(self._build_url(), json=payload, timeout=10)


def build_daily_summary_message(summary: dict[str, Any]) -> str:
    return "\n\n".join(build_daily_summary_messages(summary)).strip()


def build_daily_summary_messages(summary: dict[str, Any]) -> list[str]:
    telegram_native_brief = dict(summary.get("telegram_native_brief") or {})
    native_messages = telegram_native_brief.get("messages")
    if isinstance(native_messages, list) and native_messages:
        return [str(item).strip() for item in native_messages if str(item).strip()]

    chief_analysis = dict(summary.get("chief_analysis") or {})
    if chief_analysis:
        return _build_chief_analysis_messages(summary, chief_analysis)

    run_id = str(summary.get("run_id") or "").strip()
    vnindex_context = dict(summary.get("vnindex_context") or {})
    news_impact = dict(summary.get("news_impact") or {})
    long_candidates = dict(summary.get("long_candidates") or {})
    entry_execution = dict(summary.get("entry_execution") or {})
    top_opportunities = [dict(item) for item in (summary.get("top_opportunities") or []) if isinstance(item, dict)]
    watchlist_candidates = [dict(item) for item in (summary.get("watchlist_candidates") or []) if isinstance(item, dict)]

    messages = [
        _build_market_message(run_id, vnindex_context, summary),
        _build_news_message(run_id, news_impact),
        _build_top5_message(run_id, long_candidates, top_opportunities, watchlist_candidates),
        _build_entry_message(run_id, entry_execution, top_opportunities, watchlist_candidates),
    ]
    return [message for message in messages if message.strip()]


def _build_chief_analysis_messages(summary: dict[str, Any], chief_analysis: dict[str, Any]) -> list[str]:
    title = _clean_text(str(chief_analysis.get("title") or "Nhận định thị trường").strip())
    update_line = _clean_text(str(chief_analysis.get("update_line") or f"Cập nhật: {summary.get('run_id')}").strip())
    overview = _clean_text(str(chief_analysis.get("summary") or summary.get("headline") or "").strip())
    stance = _clean_text(str(chief_analysis.get("stance") or "").strip())
    confidence = _clean_text(str(chief_analysis.get("confidence") or "").strip())
    sections = [dict(item) for item in (chief_analysis.get("sections") or []) if isinstance(item, dict)]
    total = len(sections) + 1

    header_lines = [
        f"[1/{total}] {title}",
        update_line,
    ]
    if overview:
        header_lines.extend(["", overview])
    if stance or confidence:
        header_lines.extend([
            "",
            f"Bias: {stance or 'trung tính'} | Độ tin cậy: {confidence or 'chưa rõ'}",
        ])

    messages = ["\n".join(line for line in header_lines if line).strip()]
    for index, section in enumerate(sections, start=2):
        title_line = _clean_text(str(section.get("title") or f"Mục {index - 1}").strip())
        paragraphs = [
            _clean_text(str(item).strip())
            for item in (section.get("paragraphs") or [])
            if str(item).strip()
        ]
        bullets = [
            _clean_text(str(item).strip())
            for item in (section.get("bullets") or [])
            if str(item).strip()
        ]

        lines = [f"[{index}/{total}] {title_line}"]
        if paragraphs:
            lines.append("")
            lines.extend(paragraphs)
        if bullets:
            lines.append("")
            lines.append("Các ý chính:")
            lines.extend([f"- {item}" for item in bullets])
        messages.append("\n".join(lines).strip())

    return [message for message in messages if message.strip()]


def _build_market_message(run_id: str, vnindex_context: dict[str, Any], summary: dict[str, Any]) -> str:
    metrics = dict(vnindex_context.get("metrics") or {})
    bullets = _take_list(vnindex_context.get("bullets"), 4)
    sector_bullets = _take_list(vnindex_context.get("sector_bullets"), 2)
    action_bias = _clean_text(str(vnindex_context.get("action_bias") or "").strip())
    risk_note = _clean_text(str(vnindex_context.get("risk_note") or "").strip())
    headline = _clean_text(str(vnindex_context.get("headline") or "VNINDEX đang trong giai đoạn theo dõi thêm.").strip())
    execution_quality = _execution_quality_text(str(summary.get("execution_quality") or "unknown"))

    lines = [
        "[1/4] Phân tích thị trường chung - VNINDEX",
        f"Cập nhật: {run_id}",
        "",
        headline,
    ]

    advancers = _to_int(metrics.get("advancers"))
    decliners = _to_int(metrics.get("decliners"))
    total_symbols = _to_int(metrics.get("total_symbols"))
    positive_ratio = _to_float(metrics.get("positive_ratio"))
    ad_ratio = _to_float(metrics.get("advance_decline_ratio"))
    avg_return_3m = _to_float(metrics.get("avg_return_3m"))
    liquidity_share = _to_float(metrics.get("top_n_liquidity_share"))

    if total_symbols > 0:
        lines.append(
            f"Số liệu nhanh: {advancers}/{total_symbols} mã tăng, {decliners}/{total_symbols} mã giảm; positive ratio {_fmt_pct(positive_ratio, scale=100)}; A/D {_fmt_num(ad_ratio, 2)}."
        )
    if avg_return_3m is not None:
        lines.append(f"Xung lực trung hạn của rổ theo dõi hiện ở mức {_fmt_pct(avg_return_3m, scale=100)}.")
    if liquidity_share is not None:
        lines.append(f"Mức độ tập trung dòng tiền vào nhóm dẫn dắt đang ở khoảng {_fmt_pct(liquidity_share, scale=100)}.")
    lines.append(f"Chất lượng dữ liệu hiện tại: {execution_quality}.")

    if bullets:
        lines.extend(["", "Các điểm đáng chú ý:"])
        lines.extend([f"- {_clean_text(item)}" for item in bullets])
    if sector_bullets:
        lines.extend(["", "Nhóm ngành:"])
        lines.extend([f"- {_clean_text(item)}" for item in sector_bullets])

    if action_bias:
        lines.extend(["", "Hành động ưu tiên:", f"- {action_bias}"])
    if risk_note:
        lines.extend(["", "Rủi ro chính:", f"- {risk_note}"])

    return "\n".join(lines).strip()


def _build_news_message(run_id: str, news_impact: dict[str, Any]) -> str:
    headline = _clean_text(str(news_impact.get("headline") or "Tin tức hiện chưa đủ mạnh để đảo chiều tâm lý toàn thị trường.").strip())
    positive_items = _take_list(news_impact.get("positive_items"), 4)
    negative_items = _take_list(news_impact.get("negative_items"), 4)
    shock_items = _take_list(news_impact.get("shock_items"), 3)
    symbol_notes = _take_list(news_impact.get("symbol_notes"), 3)
    conclusion = _clean_text(str(news_impact.get("conclusion") or "Ưu tiên phản ứng giá hơn là đoán headline.").strip())

    lines = [
        "[2/4] Tin tức và yếu tố ảnh hưởng thị trường",
        f"Cập nhật: {run_id}",
        "",
        headline,
    ]
    if positive_items:
        lines.extend(["", "Tin tốt / catalyst:"])
        lines.extend([f"- {_clean_text(item)}" for item in positive_items])
    if negative_items:
        lines.extend(["", "Tin xấu / áp lực:"])
        lines.extend([f"- {_clean_text(item)}" for item in negative_items])
    if shock_items:
        lines.extend(["", "Tin sốc / cảnh báo:"])
        lines.extend([f"- {_clean_text(item)}" for item in shock_items])
    if symbol_notes:
        lines.extend(["", "Liên hệ tới cổ phiếu:"])
        lines.extend([f"- {_clean_text(item)}" for item in symbol_notes])
    lines.extend(["", "Kết luận nhanh:", f"- {conclusion}"])
    return "\n".join(lines).strip()


def _build_top5_message(run_id: str, long_candidates: dict[str, Any], top_opportunities: list[dict[str, Any]], watchlist_candidates: list[dict[str, Any]]) -> str:
    selected = [dict(item) for item in (long_candidates.get("selected") or []) if isinstance(item, dict)]
    if not selected:
        selected = [dict(item) for item in top_opportunities if isinstance(item, dict)]
    headline = _clean_text(str(long_candidates.get("headline") or "Danh sách dưới đây ưu tiên các mã LONG khỏe nhất hiện tại.").strip())
    selection_rule = _clean_text(str(long_candidates.get("selection_rule") or "Ưu tiên mã tăng giá, giữ xung lực dương và có vùng mua rõ ràng.").strip())

    lines = [
        "[3/4] Top 5 cổ phiếu LONG khỏe",
        f"Cập nhật: {run_id}",
        "",
        headline,
        f"Bộ lọc sử dụng: {selection_rule}",
    ]
    if not selected:
        lines.append("Hiện chưa có mã nào đủ chuẩn LONG khỏe để đưa vào kế hoạch mua mới.")
        if watchlist_candidates:
            lines.extend(["", "Các mã chỉ nên để ở trạng thái theo dõi:"])
            for index, item in enumerate(watchlist_candidates[:3], start=1):
                symbol = str(item.get("symbol") or "").strip().upper()
                trigger = str(item.get("trigger") or "").strip()
                rr = _to_float(item.get("risk_reward"))
                lines.append(f"{index}. {symbol}")
                if trigger:
                    lines.append(f"- Vùng theo dõi: {trigger}")
                if rr is not None:
                    lines.append(f"- RR tham chiếu: {rr:.2f}")
                note = _clean_text(str(item.get("selection_note") or "Chưa đủ xác nhận để nâng thành ý tưởng LONG.").strip())
                lines.append(f"- Trạng thái: {note}")
        return "\n".join(lines).strip()

    for index, item in enumerate(selected[:5], start=1):
        symbol = str(item.get("symbol") or "").strip().upper()
        day_change = _fmt_signed_pct(_to_float(item.get("day_change_pct")))
        period_change = _fmt_signed_pct(_to_float(item.get("period_change_pct")))
        volume_ratio = _to_float(item.get("volume_ratio"))
        rr = _to_float(item.get("risk_reward"))
        reasons = [str(reason).strip() for reason in (item.get("selection_reasons") or []) if str(reason).strip()]
        trigger = str(item.get("trigger") or "").strip()

        lines.extend([
            "",
            f"{index}. {symbol}",
            f"- Biến động phiên: {day_change if day_change else 'n/a'} | Chu kỳ theo dõi: {period_change if period_change else 'n/a'}",
        ])
        if volume_ratio is not None:
            lines.append(f"- Khối lượng so với trung bình: {volume_ratio:.2f}x")
        if rr is not None:
            lines.append(f"- RR tham chiếu: {rr:.2f}")
        if trigger:
            lines.append(f"- Vùng theo dõi: {trigger}")
        if reasons:
            lines.append(f"- Lý do chọn: {'; '.join(_clean_text(reason) for reason in reasons[:3])}.")
        note = _clean_text(str(item.get("selection_note") or "").strip())
        if note:
            lines.append(f"- Nhận định nhanh: {note}")
    return "\n".join(lines).strip()


def _build_entry_message(run_id: str, entry_execution: dict[str, Any], top_opportunities: list[dict[str, Any]], watchlist_candidates: list[dict[str, Any]]) -> str:
    entries = [dict(item) for item in (entry_execution.get("entries") or []) if isinstance(item, dict)]
    if not entries:
        entries = _fallback_entries(top_opportunities)
    posture = _clean_text(str(entry_execution.get("portfolio_posture") or "Giải ngân chậm và ưu tiên xác nhận.").strip())
    global_rules = _take_list(entry_execution.get("global_rules"), 4)

    lines = [
        "[4/4] Kế hoạch vào lệnh và quản trị vị thế",
        f"Cập nhật: {run_id}",
        "",
        f"Tư thế danh mục: {posture}",
    ]
    if global_rules:
        lines.extend(["", "Nguyên tắc chung:"])
        lines.extend([f"- {_clean_text(rule)}" for rule in global_rules])
    if entries:
        lines.extend(["", "Kế hoạch theo từng mã:"])
        for entry in entries[:5]:
            symbol = str(entry.get("symbol") or "").strip().upper()
            entry_zone = _clean_text(str(entry.get("entry_zone") or "chờ vùng mua rõ hơn").strip())
            allocation_plan = [str(item).strip() for item in (entry.get("allocation_plan") or []) if str(item).strip()]
            stop_note = _clean_text(str(entry.get("stop_note") or "Luôn đặt điểm vô hiệu trước khi vào lệnh.").strip())
            take_profit_note = _clean_text(str(entry.get("take_profit_note") or "Chốt lời từng phần khi giá tiến vào vùng cản.").strip())

            lines.append(f"- {symbol}: vùng mua {entry_zone}.")
            for plan in allocation_plan[:3]:
                lines.append(f"  • {_clean_text(plan)}")
            lines.append(f"  • {stop_note}")
            lines.append(f"  • {take_profit_note}")
    else:
        lines.extend([
            "",
            "Hiện chưa có kế hoạch vào lệnh mới vì chưa có mã đạt chuẩn LONG_READY.",
        ])
        if watchlist_candidates:
            lines.append("Tạm thời chỉ giữ watchlist và chờ giá xác nhận tốt hơn trước khi giải ngân.")
    return "\n".join(lines).strip()


def _fallback_entries(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in opportunities[:5]:
        entries.append(
            {
                "symbol": item.get("symbol"),
                "entry_zone": item.get("trigger"),
                "allocation_plan": [
                    "30% vị thế thăm dò khi giá chạm đúng vùng theo dõi.",
                    "30% tiếp theo khi giá giữ được nền và thanh khoản không xấu đi.",
                    "40% còn lại chỉ thêm khi thị trường chung thuận lợi hơn.",
                ],
                "stop_note": f"Dừng lại nếu {_clean_text(str(item.get('invalidation') or 'gãy cấu trúc hỗ trợ')).lower().rstrip('.')}.",
                "take_profit_note": f"Chốt lời từng phần theo RR tham chiếu {item.get('risk_reward') or 'n/a'}.",
            }
        )
    return entries


def _clean_text(text: str) -> str:
    cleaned = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    replacements = {
        "risk_off": "thận trọng",
        "risk_on": "tích cực",
        "balanced": "cân bằng",
        "narrow_leadership": "phân hóa hẹp",
        "downtrend": "xu hướng giảm",
        "uptrend": "xu hướng tăng",
        "pullback_buy": "mua khi điều chỉnh",
        "breakout_or_wait": "chờ xác nhận bứt phá",
        "avoid_or_wait": "chưa ưu tiên hành động",
        "healthy": "ổn định",
        "degraded": "cần kiểm tra thêm",
        "partial": "chưa hoàn chỉnh",
        "No market-wide news detected.": "Hiện chưa có cụm tin thị trường đủ mạnh để tạo lợi thế thông tin rõ rệt.",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned.strip()


def _take_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


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


def _fmt_signed_pct(value: float | None) -> str:
    if value is None:
        return ""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _execution_quality_text(value: str) -> str:
    mapping = {
        "healthy": "ổn định",
        "degraded": "cần kiểm tra thêm",
        "partial": "chưa hoàn chỉnh",
        "unknown": "chưa rõ",
    }
    key = str(value or "").strip().lower()
    return mapping.get(key, key or "chưa rõ")


def _plain_text_message(message: str) -> str:
    return str(message or "").replace("\r\n", "\n").strip()


def _chunk_message(message: str, max_length: int = MAX_TELEGRAM_TEXT_LENGTH) -> list[str]:
    text = _plain_text_message(message)
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_length)
        if split_at < max_length // 2:
            split_at = remaining.rfind(" ", 0, max_length)
        if split_at < max_length // 2:
            split_at = max_length
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return [chunk for chunk in chunks if chunk]
