# models/analysis_package.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo


DictStrAny = dict[str, Any]
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass(slots=True)
class AnalysisPackage:
    symbol: str
    company: DictStrAny
    price_summary: DictStrAny
    financial_summary: DictStrAny | None = None
    news_summary: DictStrAny | None = None
    signals: DictStrAny = field(default_factory=dict)
    risks: DictStrAny = field(default_factory=dict)
    breadth_context: DictStrAny | None = None
    data_quality: DictStrAny = field(default_factory=dict)
    missing_sections: list[str] = field(default_factory=list)
    provider_metadata: DictStrAny = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(VIETNAM_TZ))

    OPTIONAL_SECTION_FIELDS: ClassVar[tuple[str, ...]] = (
        "financial_summary",
        "news_summary",
        "breadth_context",
    )
    REQUIRED_DICT_FIELDS: ClassVar[tuple[str, ...]] = (
        "company",
        "price_summary",
        "signals",
        "risks",
        "data_quality",
        "provider_metadata",
    )

    def __post_init__(self) -> None:
        self.validate()

    def to_dict(self) -> DictStrAny:
        return {
            "symbol": self.symbol,
            "company": dict(self.company),
            "price_summary": dict(self.price_summary),
            "financial_summary": _copy_optional_dict(self.financial_summary),
            "news_summary": _copy_optional_dict(self.news_summary),
            "signals": dict(self.signals),
            "risks": dict(self.risks),
            "breadth_context": _copy_optional_dict(self.breadth_context),
            "data_quality": dict(self.data_quality),
            "missing_sections": list(self.missing_sections),
            "provider_metadata": dict(self.provider_metadata),
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AnalysisPackage:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")

        generated_at = _coerce_datetime(payload.get("generated_at"))

        return cls(
            symbol=_coerce_symbol(payload.get("symbol")),
            company=_coerce_required_dict(payload.get("company"), field_name="company"),
            price_summary=_coerce_required_dict(
                payload.get("price_summary"),
                field_name="price_summary",
            ),
            financial_summary=_coerce_optional_dict(
                payload.get("financial_summary"),
                field_name="financial_summary",
            ),
            news_summary=_coerce_optional_dict(
                payload.get("news_summary"),
                field_name="news_summary",
            ),
            signals=_coerce_required_dict(payload.get("signals", {}), field_name="signals"),
            risks=_coerce_required_dict(payload.get("risks", {}), field_name="risks"),
            breadth_context=_coerce_optional_dict(
                payload.get("breadth_context"),
                field_name="breadth_context",
            ),
            data_quality=_coerce_required_dict(
                payload.get("data_quality", {}),
                field_name="data_quality",
            ),
            missing_sections=_coerce_missing_sections(payload.get("missing_sections")),
            provider_metadata=_coerce_required_dict(
                payload.get("provider_metadata", {}),
                field_name="provider_metadata",
            ),
            generated_at=generated_at,
        )

    def validate(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")

        self.symbol = self.symbol.strip().upper()

        for field_name in self.REQUIRED_DICT_FIELDS:
            value = getattr(self, field_name)
            if not isinstance(value, dict):
                raise TypeError(f"{field_name} must be a dictionary")

        for field_name in self.OPTIONAL_SECTION_FIELDS:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, dict):
                raise TypeError(f"{field_name} must be a dictionary or None")

        if not isinstance(self.missing_sections, list):
            raise TypeError("missing_sections must be a list[str]")

        if not all(isinstance(item, str) and item.strip() for item in self.missing_sections):
            raise TypeError("missing_sections must be a list[str]")

        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime")

        self.missing_sections = self._normalize_missing_sections()

    def _normalize_missing_sections(self) -> list[str]:
        detected = self._detect_missing_sections()
        combined = [*self.missing_sections, *detected]

        normalized: list[str] = []
        seen: set[str] = set()

        for item in combined:
            name = item.strip()
            if name and name not in seen:
                normalized.append(name)
                seen.add(name)

        return normalized

    def _detect_missing_sections(self) -> list[str]:
        missing_sections: list[str] = []

        if not self.financial_summary:
            missing_sections.append("financial_summary")
        if not self.news_summary:
            missing_sections.append("news_summary")
        if not self.breadth_context:
            missing_sections.append("breadth_context")

        return missing_sections


def _copy_optional_dict(value: DictStrAny | None) -> DictStrAny | None:
    return None if value is None else dict(value)


def _coerce_symbol(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol must be a non-empty string")
    return value.strip().upper()


def _coerce_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.now(VIETNAM_TZ)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError("generated_at must be a datetime, ISO string, or None")


def _coerce_required_dict(value: Any, *, field_name: str) -> DictStrAny:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dictionary")
    return dict(value)


def _coerce_optional_dict(value: Any, *, field_name: str) -> DictStrAny | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dictionary or None")
    return dict(value)


def _coerce_missing_sections(value: Any) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise TypeError("missing_sections must be a list[str]")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TypeError("missing_sections must be a list[str]")
        normalized.append(item.strip())

    return normalized
