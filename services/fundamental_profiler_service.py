from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_fundamental_profiles(
    *,
    symbol_payloads: dict[str, dict[str, Any]] | None,
) -> DictStrAny:
    payloads = symbol_payloads or {}
    profiles: list[DictStrAny] = []
    for symbol, payload in sorted(payloads.items()):
        if not isinstance(payload, dict):
            continue
        financial_summary = dict(payload.get("financial_summary") or {})
        company = dict(payload.get("company") or {})
        available = bool(financial_summary)
        profiles.append(
            {
                "symbol": str(symbol).strip().upper(),
                "company_name": company.get("name") or company.get("company_name"),
                "financials_available": available,
                "source": financial_summary.get("source") if available else None,
            }
        )

    available_count = sum(1 for item in profiles if item.get("financials_available"))
    return {
        "status": "ready" if profiles else "missing",
        "summary": f"Fundamental profiler co du lieu tai chinh cho {available_count}/{len(profiles)} symbol." if profiles else "Chua co du lieu fundamental.",
        "profiles": profiles,
    }
