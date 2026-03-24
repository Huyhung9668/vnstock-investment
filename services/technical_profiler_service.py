from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_technical_profiles(
    *,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
) -> DictStrAny:
    payloads = trade_plan_payloads or {}
    profiles: list[DictStrAny] = []
    for symbol, payload in sorted(payloads.items()):
        if not isinstance(payload, dict):
            continue
        entry_zone = dict(payload.get("entry_zone") or {})
        profiles.append(
            {
                "symbol": str(symbol).strip().upper(),
                "setup_type": payload.get("setup_type"),
                "trigger": _entry_zone_text(entry_zone),
                "risk_reward": payload.get("risk_reward"),
                "invalidation": payload.get("invalidation"),
                "degraded_mode": bool(payload.get("degraded_mode")),
            }
        )

    return {
        "status": "ready" if profiles else "missing",
        "summary": f"Technical profiler da lap ho so cho {len(profiles)} symbol." if profiles else "Chua co technical profiles.",
        "profiles": profiles,
    }


def _entry_zone_text(entry_zone: DictStrAny) -> str:
    low = entry_zone.get("low")
    high = entry_zone.get("high")
    strategy = str(entry_zone.get("strategy", "")).strip()
    if low is None and high is None:
        return strategy or "wait"
    return f"{low} - {high} ({strategy or 'entry'})"
