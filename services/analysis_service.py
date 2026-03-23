from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.analysis_package import AnalysisPackage
from providers.base import TradePlanningProvider
from services.analysis_builder import build_analysis_package


DictStrAny = dict[str, Any]


@dataclass(slots=True)
class AnalysisServiceResult:
    analysis_package: AnalysisPackage
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    degraded: bool = False
    runtime_context: DictStrAny = field(default_factory=dict)


def build_analysis_result(
    *,
    provider: TradePlanningProvider,
    symbol: str,
    runtime_config: dict[str, Any] | None = None,
) -> AnalysisServiceResult:
    analysis_package = build_analysis_package(provider, symbol)

    warnings = _build_warnings(analysis_package)
    errors: list[str] = []
    degraded = bool(analysis_package.missing_sections)
    runtime_context = _build_runtime_context(runtime_config)

    return AnalysisServiceResult(
        analysis_package=analysis_package,
        warnings=warnings,
        errors=errors,
        degraded=degraded,
        runtime_context=runtime_context,
    )


def _build_warnings(analysis_package: AnalysisPackage) -> list[str]:
    warnings: list[str] = []

    if analysis_package.missing_sections:
        warnings.append(
            "Missing optional sections: "
            + ", ".join(f"`{section}`" for section in analysis_package.missing_sections)
        )

    provider_health = analysis_package.data_quality.get("provider_health")
    if isinstance(provider_health, dict):
        status = str(provider_health.get("status", "")).strip().lower()
        if status and status not in {"ok", "healthy", "ready"}:
            warnings.append("Provider health indicates a degraded state.")

    return warnings


def _build_runtime_context(runtime_config: dict[str, Any] | None) -> DictStrAny:
    if runtime_config is None:
        return {}
    if not isinstance(runtime_config, dict):
        raise TypeError("runtime_config must be a dictionary or None")
    return dict(runtime_config)
