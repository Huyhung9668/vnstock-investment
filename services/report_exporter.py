from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from models.analysis_package import AnalysisPackage


DictStrAny = dict[str, Any]
DEFAULT_REPORTS_DIR = Path("reports")


@dataclass(slots=True)
class ReportExportResult:
    output_path: str
    files_created: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    data_quality_summary: DictStrAny = field(default_factory=dict)


def build_data_quality_summary(analysis_package: AnalysisPackage) -> DictStrAny:
    provider_name = _stringify(analysis_package.provider_metadata.get("provider_name"), default="unknown")
    section_statuses = _extract_section_statuses(analysis_package.data_quality)
    overall_status = _derive_overall_status(
        missing_sections=analysis_package.missing_sections,
        provider_health=analysis_package.data_quality.get("provider_health"),
    )

    return {
        "symbol": analysis_package.symbol,
        "provider_name": provider_name,
        "generated_at": analysis_package.generated_at.isoformat(),
        "missing_sections": list(analysis_package.missing_sections),
        "overall_status": overall_status,
        "section_statuses": section_statuses,
    }


def ensure_data_quality_section(markdown_text: str, analysis_package: AnalysisPackage) -> str:
    normalized_markdown = _validate_markdown_text(markdown_text)
    if "## Data coverage / Data quality" in normalized_markdown:
        return normalized_markdown

    summary = build_data_quality_summary(analysis_package)
    missing_text = _format_missing_sections(summary["missing_sections"])

    section_lines = [
        "## Data coverage / Data quality",
        f"- provider: `{summary['provider_name']}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- missing_sections: {missing_text}",
        f"- overall_status: `{summary['overall_status']}`",
    ]

    return normalized_markdown.rstrip() + "\n\n" + "\n".join(section_lines) + "\n"


def export_markdown_report(
    *,
    analysis_package: AnalysisPackage,
    markdown_text: str,
    output_path: str | None = None,
) -> ReportExportResult:
    _validate_analysis_package(analysis_package)
    normalized_markdown = ensure_data_quality_section(markdown_text, analysis_package)
    resolved_output_path = _resolve_output_path(analysis_package.symbol, output_path)
    data_quality_summary = build_data_quality_summary(analysis_package)

    warnings = _build_warnings(analysis_package)
    errors: list[str] = []
    files_created: list[str] = []

    try:
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(normalized_markdown, encoding="utf-8")
        files_created.append(str(resolved_output_path))
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        raise

    return ReportExportResult(
        output_path=str(resolved_output_path),
        files_created=files_created,
        warnings=warnings,
        errors=errors,
        data_quality_summary=data_quality_summary,
    )


def _validate_analysis_package(analysis_package: AnalysisPackage) -> None:
    if not isinstance(analysis_package, AnalysisPackage):
        raise TypeError("analysis_package must be an AnalysisPackage")
    analysis_package.validate()


def _validate_markdown_text(markdown_text: str) -> str:
    if not isinstance(markdown_text, str):
        raise TypeError("markdown_text must be a string")

    normalized = markdown_text.strip()
    if not normalized:
        raise ValueError("markdown_text must not be empty")

    return normalized


def _resolve_output_path(symbol: str, output_path: str | None) -> Path:
    if output_path is not None:
        path = Path(output_path)
        if not str(path).strip():
            raise ValueError("output_path must not be empty")
        return path

    return DEFAULT_REPORTS_DIR / f"trade_plan_{symbol.lower()}.md"


def _extract_section_statuses(data_quality: DictStrAny) -> DictStrAny:
    raw_sections = data_quality.get("sections")
    if not isinstance(raw_sections, dict):
        return {}

    section_statuses: DictStrAny = {}
    for section_name in sorted(raw_sections):
        section_value = raw_sections.get(section_name)
        if not isinstance(section_value, dict):
            continue

        section_statuses[section_name] = {
            "status": _stringify(section_value.get("status"), default="unknown"),
            "present": bool(section_value.get("present", False)),
        }

        if "error_type" in section_value:
            section_statuses[section_name]["error_type"] = _stringify(
                section_value.get("error_type"),
                default="unknown",
            )

    return section_statuses


def _derive_overall_status(*, missing_sections: list[str], provider_health: Any) -> str:
    if _provider_health_has_error(provider_health):
        return "low"

    missing_count = len(missing_sections)
    if missing_count == 0:
        return "high"
    if missing_count <= 2:
        return "medium"
    return "low"


def _provider_health_has_error(provider_health: Any) -> bool:
    if not isinstance(provider_health, dict):
        return False

    status = _stringify(provider_health.get("status"), default="unknown").lower()
    return status not in {"ok", "healthy", "ready"}


def _build_warnings(analysis_package: AnalysisPackage) -> list[str]:
    warnings: list[str] = []

    if analysis_package.missing_sections:
        warnings.append(
            "Missing optional sections: "
            + ", ".join(f"`{item}`" for item in sorted(set(analysis_package.missing_sections)))
        )

    provider_health = analysis_package.data_quality.get("provider_health")
    if _provider_health_has_error(provider_health):
        warnings.append("Provider health indicates a non-ok status.")

    return warnings


def _format_missing_sections(missing_sections: list[str]) -> str:
    if not missing_sections:
        return "`none`"
    return ", ".join(f"`{item}`" for item in sorted(set(missing_sections)))


def _stringify(value: Any, *, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip()
        return text if text else default
    return str(value)
