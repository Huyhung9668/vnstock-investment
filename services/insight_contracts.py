from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]


def build_analyst_brief(
    *,
    insight: str,
    evidence: list[str] | None = None,
    implication: str | None = None,
    action: str | None = None,
    risk: str | None = None,
) -> DictStrAny:
    normalized_evidence = [str(item).strip() for item in (evidence or []) if str(item).strip()]
    return {
        "insight": str(insight).strip(),
        "evidence": normalized_evidence,
        "implication": str(implication).strip() if implication else "",
        "action": str(action).strip() if action else "",
        "risk": str(risk).strip() if risk else "",
    }


def summarize_brief(brief: dict[str, Any] | None) -> str:
    if not isinstance(brief, dict):
        return ""
    parts = [
        str(brief.get("insight", "")).strip(),
        str(brief.get("implication", "")).strip(),
        str(brief.get("action", "")).strip(),
    ]
    return " ".join(part for part in parts if part)
