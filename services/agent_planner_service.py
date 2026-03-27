from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_agent_plan(*, objective: str, send_telegram: bool, export_reports: bool) -> DictStrAny:
    normalized = str(objective or "").strip().lower()

    requested = {
        "market": any(token in normalized for token in ["thị trường", "thi truong", "vnindex", "market"]),
        "news": any(token in normalized for token in ["tin", "news", "catalyst", "shock"]),
        "long": any(token in normalized for token in ["long", "top 5", "top5", "cổ phiếu", "co phieu"]),
        "entry": any(token in normalized for token in ["entry", "vào lệnh", "vao lenh", "giải ngân", "giai ngan"]),
        "telegram": send_telegram or any(token in normalized for token in ["telegram", "tele"]),
        "report": export_reports or any(token in normalized for token in ["báo cáo", "bao cao", "report", "dashboard"]),
    }

    if not any(requested.values()):
        requested["market"] = True
        requested["news"] = True
        requested["long"] = True
        requested["entry"] = True

    plan = [
        "env_setup",
        "source_health",
        "market_overview",
        "ranking_selection",
        "deep_dive",
        "trade_plan",
        "daily_briefing",
    ]
    if requested["market"]:
        plan.append("vnindex_context")
    if requested["news"]:
        plan.append("news_impact")
    if requested["long"]:
        plan.append("long_candidate_selector")
    if requested["entry"]:
        plan.append("entry_execution")
    plan.append("quality_gates")
    if requested["report"]:
        plan.extend(["export_reports", "write_manifest"])
    if requested["telegram"]:
        plan.append("telegram_market_brief")

    deduped: list[str] = []
    seen: set[str] = set()
    for step in plan:
        if step not in seen:
            seen.add(step)
            deduped.append(step)

    return {
        "objective": objective,
        "requested_capabilities": requested,
        "steps": deduped,
        "summary": _build_summary(requested, deduped),
    }


def _build_summary(requested: dict[str, bool], steps: list[str]) -> str:
    active = [name for name, enabled in requested.items() if enabled]
    return f"Agent planner chọn {len(steps)} bước cho mục tiêu hiện tại; trọng tâm = {', '.join(active) or 'market analysis'}."
