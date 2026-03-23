from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


DictStrAny = dict[str, Any]


@dataclass(slots=True)
class ReportManifest:
    run_id: str
    run_date: datetime
    symbols: list[str]
    mode: str
    source_used: str
    files_created: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    data_quality_summary: DictStrAny = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def to_dict(self) -> DictStrAny:
        return {
            "run_id": self.run_id,
            "run_date": self.run_date.isoformat(),
            "symbols": list(self.symbols),
            "mode": self.mode,
            "source_used": self.source_used,
            "files_created": list(self.files_created),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "duration_seconds": self.duration_seconds,
            "data_quality_summary": dict(self.data_quality_summary),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReportManifest:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")

        return cls(
            run_id=_coerce_non_empty_string(payload.get("run_id"), field_name="run_id"),
            run_date=_coerce_datetime(payload.get("run_date")),
            symbols=_coerce_string_list(payload.get("symbols"), field_name="symbols", uppercase=True),
            mode=_coerce_non_empty_string(payload.get("mode"), field_name="mode"),
            source_used=_coerce_non_empty_string(payload.get("source_used"), field_name="source_used"),
            files_created=_coerce_string_list(
                payload.get("files_created", []),
                field_name="files_created",
                uppercase=False,
            ),
            warnings=_coerce_string_list(payload.get("warnings", []), field_name="warnings", uppercase=False),
            errors=_coerce_string_list(payload.get("errors", []), field_name="errors", uppercase=False),
            duration_seconds=_coerce_duration(payload.get("duration_seconds", 0.0)),
            data_quality_summary=_coerce_required_dict(
                payload.get("data_quality_summary", {}),
                field_name="data_quality_summary",
            ),
        )

    def validate(self) -> None:
        self.run_id = _coerce_non_empty_string(self.run_id, field_name="run_id")
        self.run_date = _coerce_datetime(self.run_date)
        self.symbols = _coerce_string_list(self.symbols, field_name="symbols", uppercase=True)
        self.mode = _coerce_non_empty_string(self.mode, field_name="mode")
        self.source_used = _coerce_non_empty_string(self.source_used, field_name="source_used")
        self.files_created = _coerce_string_list(
            self.files_created,
            field_name="files_created",
            uppercase=False,
        )
        self.warnings = _coerce_string_list(self.warnings, field_name="warnings", uppercase=False)
        self.errors = _coerce_string_list(self.errors, field_name="errors", uppercase=False)
        self.duration_seconds = _coerce_duration(self.duration_seconds)
        self.data_quality_summary = _coerce_required_dict(
            self.data_quality_summary,
            field_name="data_quality_summary",
        )


def _coerce_non_empty_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError("run_date must be a datetime or ISO string")


def _coerce_string_list(value: Any, *, field_name: str, uppercase: bool) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list[str]")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TypeError(f"{field_name} must be a list[str]")
        text = item.strip()
        normalized.append(text.upper() if uppercase else text)

    return normalized


def _coerce_required_dict(value: Any, *, field_name: str) -> DictStrAny:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dictionary")
    return dict(value)


def _coerce_duration(value: Any) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError("duration_seconds must be a number")

    duration = float(value)
    if duration < 0:
        raise ValueError("duration_seconds must be greater than or equal to 0")

    return duration
