from __future__ import annotations

from typing import Any

import pandas as pd


DictStrAny = dict[str, Any]


def build_market_synthesis(
    *,
    run_id: str,
    selection_mode: str,
    market_overview: dict[str, Any] | None,
    ranking_table: pd.DataFrame | None,
    top_opportunities: list[dict[str, Any]] | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    execution_status: dict[str, Any] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_symbols = {str(key).strip().upper(): dict(value) for key, value in (symbol_payloads or {}).items()}
    normalized_trade_plans = {
        str(key).strip().upper(): dict(value) for key, value in (trade_plan_payloads or {}).items()
    }
    normalized_execution = dict(execution_status or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    normalized_opportunities = [dict(item) for item in (top_opportunities or []) if isinstance(item, dict)]
    normalized_ranking = ranking_table.copy() if isinstance(ranking_table, pd.DataFrame) else pd.DataFrame()

    regime = _ensure_dict(normalized_market.get("regime"))
    breadth = _ensure_dict(normalized_market.get("breadth"))
    index_context = _ensure_dict(normalized_market.get("index_context"))
    liquidity_concentration = _ensure_dict(normalized_market.get("liquidity_concentration"))

    top_stock_focus = _build_top_stock_focus(
        opportunities=normalized_opportunities,
        symbol_payloads=normalized_symbols,
        trade_plan_payloads=normalized_trade_plans,
    )
    sector_strength = _build_sector_strength(normalized_market)
    macro_and_sentiment = _build_macro_and_sentiment(regime, index_context, normalized_warnings)
    market_state = _build_market_state(regime, breadth, index_context, normalized_execution)
    flow_of_funds = _build_flow_of_funds(liquidity_concentration, normalized_market, normalized_ranking)
    action_plan = _build_action_plan(
        top_stock_focus=top_stock_focus,
        execution_status=normalized_execution,
        warnings=normalized_warnings,
    )
    risk_watch = _build_risk_watch(
        top_stock_focus=top_stock_focus,
        execution_status=normalized_execution,
        warnings=normalized_warnings,
    )
    conclusion = _build_conclusion(
        regime=regime,
        execution_status=normalized_execution,
        top_stock_focus=top_stock_focus,
    )

    return {
        "run_id": run_id,
        "selection_mode": selection_mode,
        "stance": _infer_stance(regime, normalized_execution),
        "confidence": _infer_confidence(normalized_execution, normalized_warnings),
        "macro_and_sentiment": macro_and_sentiment,
        "market_state": market_state,
        "flow_of_funds": flow_of_funds,
        "sector_strength": sector_strength,
        "top_stock_focus": top_stock_focus,
        "action_plan": action_plan,
        "risk_watch": risk_watch,
        "conclusion": conclusion,
        "data_quality_note": _build_data_quality_note(normalized_execution, normalized_warnings),
        "warning_count": len(normalized_warnings),
    }


def _build_macro_and_sentiment(
    regime: DictStrAny,
    index_context: DictStrAny,
    warnings: list[str],
) -> list[str]:
    bullets: list[str] = []
    regime_name = _string_or_none(regime.get("regime")) or "unknown"
    explanation = _string_or_none(regime.get("explanation"))
    avg_return_3m = _string_or_none(index_context.get("avg_return_3m"))
    volatility = _string_or_none(index_context.get("volatility"))

    if explanation:
        bullets.append(f"Trang thai vi mo va sentiment hien tai nghieng ve che do {regime_name}: {explanation}")
    else:
        bullets.append(f"Boi canh vi mo hien dang o che do {regime_name}, can them xac nhan tu du lieu bo sung.")

    if avg_return_3m:
        bullets.append(f"Do manh trung han cua universe dang phan anh qua avg_return_3m = {avg_return_3m}.")
    if volatility:
        bullets.append(f"Bien dong thi truong hien tai duoc ghi nhan o muc {volatility}.")
    if any("degraded" in warning.lower() for warning in warnings):
        bullets.append("Co dau hieu degraded trong pipeline, can tach ro phan du lieu chac chan va phan can review them.")

    return bullets


def _build_market_state(
    regime: DictStrAny,
    breadth: DictStrAny,
    index_context: DictStrAny,
    execution_status: DictStrAny,
) -> list[str]:
    bullets: list[str] = []
    positive_ratio = breadth.get("positive_ratio")
    ad_ratio = breadth.get("advance_decline_ratio")
    quality = _string_or_none(execution_status.get("quality")) or "unknown"
    regime_name = _string_or_none(regime.get("regime")) or "unknown"

    bullets.append(f"Thi truong dang van dong trong che do {regime_name}; chat luong pipeline hien tai = {quality}.")

    if positive_ratio is not None:
        bullets.append(f"Do rong tang gia uoc tinh positive_ratio = {_format_number(positive_ratio)}.")
    if ad_ratio is not None:
        bullets.append(f"Ty le advance/decline hien tai = {_format_number(ad_ratio)}.")

    proxy_index = _string_or_none(index_context.get("proxy_index"))
    if proxy_index:
        bullets.append(f"Bo canh chi so dang duoc noi suy tu {proxy_index}.")

    return bullets


def _build_flow_of_funds(
    liquidity_concentration: DictStrAny,
    market_overview: DictStrAny,
    ranking_table: pd.DataFrame,
) -> list[str]:
    bullets: list[str] = []
    liquidity_share = liquidity_concentration.get("top_n_liquidity_share")
    top_symbols = liquidity_concentration.get("top_symbols")
    top_movers = _ensure_dict(market_overview.get("top_movers"))
    top_gainers = top_movers.get("top_gainers")

    if liquidity_share is not None:
        bullets.append(
            f"Dong tien tap trung vao nhom dan dat voi top_n_liquidity_share = {_format_number(liquidity_share)}."
        )

    if isinstance(top_symbols, list) and top_symbols:
        labels = []
        for item in top_symbols[:3]:
            if isinstance(item, dict) and str(item.get("symbol", "")).strip():
                labels.append(str(item.get("symbol", "")).strip().upper())
        if labels:
            bullets.append(f"Cac ma hut thanh khoan noi bat: {', '.join(labels)}.")

    if isinstance(top_gainers, list) and top_gainers:
        first = top_gainers[0]
        if isinstance(first, dict) and str(first.get("symbol", "")).strip():
            bullets.append(f"Dong tien dang uu tien nhom co xung luc gia, ma noi bat la {str(first['symbol']).strip().upper()}.")

    if not bullets and not ranking_table.empty and "symbol" in ranking_table.columns:
        symbols = [str(symbol).strip().upper() for symbol in ranking_table["symbol"].head(3).tolist() if str(symbol).strip()]
        if symbols:
            bullets.append(f"Tam thoi theo doi dong tien qua nhom ung vien top rank: {', '.join(symbols)}.")

    if not bullets:
        bullets.append("Chua du du lieu de ket luan dong tien mot cach manh.")

    return bullets


def _build_sector_strength(market_overview: DictStrAny) -> list[str]:
    sector_rotation = market_overview.get("sector_rotation")
    if not isinstance(sector_rotation, list) or not sector_rotation:
        return ["Chua co du lieu sector rotation de ket luan suc manh nganh."]

    bullets: list[str] = []
    for item in sector_rotation[:4]:
        if not isinstance(item, dict):
            continue
        sector = str(item.get("sector", "")).strip().upper()
        label = str(item.get("rotation_label", "")).strip().lower() or "neutral"
        avg_return = item.get("avg_return_3m")
        if sector:
            bullets.append(
                f"Nhom {sector} dang o trang thai {label} voi avg_return_3m = {_format_number(avg_return)}."
            )
    return bullets or ["Chua co du lieu sector rotation de ket luan suc manh nganh."]


def _build_top_stock_focus(
    *,
    opportunities: list[DictStrAny],
    symbol_payloads: dict[str, DictStrAny],
    trade_plan_payloads: dict[str, DictStrAny],
) -> list[DictStrAny]:
    focus_rows: list[DictStrAny] = []
    for item in opportunities[:5]:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        analysis = symbol_payloads.get(symbol, {})
        plan = trade_plan_payloads.get(symbol, {})
        focus_rows.append(
            {
                "symbol": symbol,
                "thesis": _string_or_none(plan.get("thesis"))
                or _string_or_none(item.get("thesis"))
                or _string_or_none(analysis.get("thesis"))
                or "Can review them de xac dinh luan diem chinh.",
                "setup_type": _string_or_none(plan.get("setup_type")) or _string_or_none(item.get("setup_type")) or "unknown",
                "trigger": _string_or_none(item.get("trigger")) or "wait",
                "risk_reward": _string_or_none(plan.get("risk_reward")) or _string_or_none(item.get("risk_reward")) or "n/a",
                "invalidation": _string_or_none(plan.get("invalidation")) or _string_or_none(item.get("invalidation")) or "Chua co invalidation ro rang.",
                "degraded_mode": bool(plan.get("degraded_mode")) or bool(item.get("degraded_mode")),
            }
        )
    return focus_rows


def _build_action_plan(
    *,
    top_stock_focus: list[DictStrAny],
    execution_status: DictStrAny,
    warnings: list[str],
) -> list[str]:
    actions: list[str] = []
    quality = _string_or_none(execution_status.get("quality")) or "unknown"

    if quality == "healthy":
        actions.append("Uu tien giam sat nhom co setup dep va chi vao lenh khi gia xac nhan quanh trigger.")
    elif quality == "degraded":
        actions.append("Can review ky cac phan degraded/fallback truoc khi bien bao cao thanh hanh dong giao dich.")
    else:
        actions.append("Tam thoi xem bao cao nhu bo context tham khao, uu tien kiem tra lai du lieu va gia.")

    symbols = [item["symbol"] for item in top_stock_focus[:3] if item.get("symbol")]
    if symbols:
        actions.append(f"Lap watchlist hanh dong ngan han cho: {', '.join(symbols)}.")

    degraded_symbols = [item["symbol"] for item in top_stock_focus if bool(item.get("degraded_mode"))]
    if degraded_symbols:
        actions.append(f"Review thu cong luan diem va muc gia cho: {', '.join(degraded_symbols[:3])}.")

    if any("rate limit" in warning.lower() for warning in warnings):
        actions.append("Neu can do phu cao hon, can tang tier API hoac tach batch de tranh rate limit.")

    return actions[:5]


def _build_risk_watch(
    *,
    top_stock_focus: list[DictStrAny],
    execution_status: DictStrAny,
    warnings: list[str],
) -> list[str]:
    risks: list[str] = []
    if any(bool(item.get("degraded_mode")) for item in top_stock_focus):
        risks.append("Mot phan top ideas dang o che do degraded, can tranh overconfidence khi dien giai.")

    failed_symbols = execution_status.get("failed_symbols")
    if isinstance(failed_symbols, int) and failed_symbols > 0:
        risks.append(f"Con {failed_symbols} symbol bi loi trong batch, bo canh hien tai chua bao phu hoan toan.")

    invalidations = [str(item.get("invalidation", "")).strip() for item in top_stock_focus[:3] if str(item.get("invalidation", "")).strip()]
    if invalidations:
        risks.append(f"Dieu kien vo hieu can theo doi sat: {invalidations[0]}")

    for warning in warnings[:3]:
        risks.append(warning)

    return risks[:6] or ["Khong co canh bao bo sung ngoai cac rui ro giao dich thong thuong."]


def _build_conclusion(
    *,
    regime: DictStrAny,
    execution_status: DictStrAny,
    top_stock_focus: list[DictStrAny],
) -> str:
    regime_name = _string_or_none(regime.get("regime")) or "unknown"
    quality = _string_or_none(execution_status.get("quality")) or "unknown"
    lead_symbol = top_stock_focus[0]["symbol"] if top_stock_focus else "watchlist"

    if quality == "healthy":
        return f"Thi truong dang o che do {regime_name}; co the uu tien theo doi {lead_symbol} nhu ung vien hanh dong so mot."
    if quality == "degraded":
        return f"Thi truong dang o che do {regime_name}, nhung pipeline con degraded; dung {lead_symbol} nhu y tuong can review thay vi auto-trade."
    return f"Bo canh hien tai nghieng ve {regime_name}, nhung chat luong thuc thi chua on dinh; can review thu cong truoc khi hanh dong voi {lead_symbol}."


def _build_data_quality_note(execution_status: DictStrAny, warnings: list[str]) -> str:
    quality = _string_or_none(execution_status.get("quality")) or "unknown"
    if quality == "healthy" and not warnings:
        return "Du lieu hien tai o muc kha dung cho viec lap watchlist hanh dong."
    if quality == "degraded":
        return "Du lieu co the dung de dinh huong, nhung can tach ro phan chac chan va phan can xac minh them."
    return "Du lieu hien tai phu hop de tham khao boi canh, chua nen xem la co so duy nhat cho quyet dinh."


def _infer_stance(regime: DictStrAny, execution_status: DictStrAny) -> str:
    regime_name = _string_or_none(regime.get("regime")) or "unknown"
    quality = _string_or_none(execution_status.get("quality")) or "unknown"
    if quality == "partial":
        return "caution"
    if regime_name in {"risk_on", "balanced"}:
        return "selective offense"
    if regime_name in {"risk_off", "narrow_leadership"}:
        return "defensive"
    return "neutral"


def _infer_confidence(execution_status: DictStrAny, warnings: list[str]) -> str:
    quality = _string_or_none(execution_status.get("quality")) or "unknown"
    if quality == "healthy" and not warnings:
        return "medium_high"
    if quality == "degraded":
        return "medium"
    return "low"


def _ensure_dict(payload: Any) -> DictStrAny:
    return dict(payload) if isinstance(payload, dict) else {}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.4f}".rstrip("0").rstrip(".")
