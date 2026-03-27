from __future__ import annotations

from typing import Any


DictStrAny = dict[str, Any]

TEMPLATE_PATTERNS = [
    "Cơ sở chính hiện tại là",
    "Điểm cần thận trọng là",
    "Ưu tiên hành động",
]


def critique_analysis(*, chief_analysis: dict[str, Any] | None) -> DictStrAny:
    analysis = dict(chief_analysis or {})
    sections = [dict(item) for item in (analysis.get("sections") or []) if isinstance(item, dict)]

    issues: list[str] = []
    rewrite_hints: list[str] = []
    for section in sections:
        paragraphs = [str(item).strip() for item in (section.get("paragraphs") or []) if str(item).strip()]
        joined = " ".join(paragraphs)
        if sum(joined.count(pattern) for pattern in TEMPLATE_PATTERNS) >= 2:
            issues.append(f"{section.get('title')}: còn mang tính template, cần viết tự nhiên hơn.")
        if len(paragraphs) >= 6:
            issues.append(f"{section.get('title')}: hơi dài, nên gom ý và chọn 2-3 luận điểm chính.")
        if "proxy" in joined.lower() or "thay thế" in joined.lower():
            rewrite_hints.append(f"{section.get('title')}: nhắc rõ dữ liệu proxy nhưng không nên lặp quá nhiều trong cùng mục.")

    score = max(0, 100 - len(issues) * 12)
    return {
        "status": "ready",
        "quality_score": score,
        "issues": issues[:8],
        "rewrite_hints": rewrite_hints[:5],
    }
