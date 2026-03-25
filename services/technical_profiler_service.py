from __future__ import annotations

from typing import Any

from services.insight_contracts import build_analyst_brief


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

    lead = profiles[0] if profiles else {}
    brief = build_analyst_brief(
        insight=(
            f"Về kỹ thuật, {lead.get('symbol')} đang là mã có vùng theo dõi rõ nhất trong nhóm ưu tiên."
            if lead.get("symbol") else "Chưa hình thành đủ hồ sơ kỹ thuật để kết luận."
        ),
        evidence=[f"Technical profiler đã lập hồ sơ cho {len(profiles)} mã."] if profiles else [],
        implication="Ưu tiên hành động ở những mã có trigger và điểm vô hiệu rõ ràng, tránh mua theo cảm tính.",
        action="Chỉ kích hoạt kế hoạch giao dịch khi giá phản ứng đúng vùng theo dõi và thanh khoản không suy yếu.",
        risk="Mọi setup đẹp đều mất hiệu lực nếu giá xuyên thủng vùng vô hiệu với áp lực bán tăng.",
    )

    return {
        "status": "ready" if profiles else "missing",
        "summary": f"Technical profiler đã lập hồ sơ cho {len(profiles)} mã." if profiles else "Chưa có technical profiles.",
        "profiles": profiles,
        "analyst_brief": brief,
    }


def _entry_zone_text(entry_zone: DictStrAny) -> str:
    low = entry_zone.get("low")
    high = entry_zone.get("high")
    strategy = str(entry_zone.get("strategy", "")).strip()
    if low is None and high is None:
        return strategy or "wait"
    return f"{low} - {high} ({strategy or 'entry'})"
