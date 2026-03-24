from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def run_quality_gates(
    *,
    market_overview: dict[str, Any] | None,
    top_opportunities: list[dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    daily_briefing: dict[str, Any] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    normalized_market = dict(market_overview or {})
    normalized_top = [dict(item) for item in (top_opportunities or []) if isinstance(item, dict)]
    normalized_trade_plans = {
        str(key).strip().upper(): dict(value)
        for key, value in (trade_plan_payloads or {}).items()
        if isinstance(value, dict)
    }
    normalized_briefing = dict(daily_briefing or {})
    normalized_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]

    checks = {
        "market_overview_ready": bool(normalized_market),
        "top_opportunities_ready": len(normalized_top) >= 3,
        "trade_plans_ready": len(normalized_trade_plans) >= 3,
        "daily_briefing_ready": bool(normalized_briefing),
        "chief_analysis_ready": bool(normalized_briefing.get("chief_analysis")),
        "skill_pipeline_ready": bool(normalized_briefing.get("skill_pipeline")),
    }

    failed = [name for name, ok in checks.items() if not ok]
    degraded = bool(normalized_warnings)
    execution_quality = str(
        normalized_briefing.get("execution_status", {}).get("quality", "unknown")
    ).strip().lower()
    if execution_quality == "partial":
        failed.append("execution_status_partial")
    if failed:
        status = "partial"
    elif degraded:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "checks": checks,
        "failed_checks": failed,
        "warning_count": len(normalized_warnings),
        "summary": _build_summary(status, failed),
    }


def _build_summary(status: str, failed_checks: list[str]) -> str:
    if status == "healthy":
        return "Tat ca quality gates chinh da dat."
    if status == "degraded":
        return "Quality gates dat muc chap nhan duoc nhung con warnings can review."
    if failed_checks:
        return "Quality gates chua dat day du: " + ", ".join(failed_checks)
    return "Quality gates chua dat."
