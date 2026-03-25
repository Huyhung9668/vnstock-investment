from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.analysis_package import AnalysisPackage
from providers.base import TradePlanningProvider


DictStrAny = dict[str, Any]


@dataclass(slots=True)
class SectionResult:
    value: DictStrAny | None
    missing: bool
    data_quality: DictStrAny


def build_analysis_package(
    provider: TradePlanningProvider,
    symbol: str,
    *,
    breadth_context_override: dict[str, Any] | None = None,
) -> AnalysisPackage:
    normalized_symbol = _normalize_symbol(symbol)
    provider_name = provider.provider_name()

    company = _get_required_section(
        section_name="company",
        fetcher=lambda: provider.get_company_profile(normalized_symbol),
    )
    price_summary = _get_required_section(
        section_name="price_summary",
        fetcher=lambda: provider.get_price_summary(normalized_symbol),
    )
    financial_summary = _get_optional_symbol_section(
        section_name="financial_summary",
        symbol=normalized_symbol,
        fetcher=provider.get_financial_summary,
    )
    news_summary = _get_optional_symbol_section(
        section_name="news_summary",
        symbol=normalized_symbol,
        fetcher=provider.get_news_summary,
    )
    if isinstance(breadth_context_override, dict) and breadth_context_override:
        breadth_context = SectionResult(
            value=dict(breadth_context_override),
            missing=False,
            data_quality=_build_optional_section_quality(
                section_name="breadth_context",
                status="ok",
                error=None,
            ),
        )
    else:
        breadth_context = _get_optional_global_section(
            section_name="breadth_context",
            fetcher=provider.get_breadth_context,
        )

    missing_sections = _build_missing_sections(
        financial_summary=financial_summary,
        news_summary=news_summary,
        breadth_context=breadth_context,
    )
    data_quality = _build_data_quality(
        provider=provider,
        company=company,
        price_summary=price_summary,
        financial_summary=financial_summary,
        news_summary=news_summary,
        breadth_context=breadth_context,
    )
    provider_metadata = _build_provider_metadata(provider_name=provider_name)

    return AnalysisPackage(
        symbol=normalized_symbol,
        company=company,
        price_summary=price_summary,
        financial_summary=financial_summary.value,
        news_summary=news_summary.value,
        signals={},
        risks={},
        breadth_context=breadth_context.value,
        data_quality=data_quality,
        missing_sections=missing_sections,
        provider_metadata=provider_metadata,
    )


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")
    return symbol.strip().upper()


def _get_required_section(
    *,
    section_name: str,
    fetcher: Callable[[], dict[str, Any]],
) -> DictStrAny:
    value = fetcher()
    return _ensure_dict(value=value, section_name=section_name, allow_none=False)


def _get_optional_symbol_section(
    *,
    section_name: str,
    symbol: str,
    fetcher: Callable[[str], dict[str, Any] | None],
) -> SectionResult:
    try:
        value = fetcher(symbol)
    except Exception as exc:
        return SectionResult(
            value=None,
            missing=True,
            data_quality=_build_optional_section_quality(
                section_name=section_name,
                status="error",
                error=exc,
            ),
        )

    normalized_value = _ensure_dict(value=value, section_name=section_name, allow_none=True)
    return SectionResult(
        value=normalized_value,
        missing=normalized_value is None,
        data_quality=_build_optional_section_quality(
            section_name=section_name,
            status="missing" if normalized_value is None else "ok",
            error=None,
        ),
    )


def _get_optional_global_section(
    *,
    section_name: str,
    fetcher: Callable[[], dict[str, Any] | None],
) -> SectionResult:
    try:
        value = fetcher()
    except Exception as exc:
        return SectionResult(
            value=None,
            missing=True,
            data_quality=_build_optional_section_quality(
                section_name=section_name,
                status="error",
                error=exc,
            ),
        )

    normalized_value = _ensure_dict(value=value, section_name=section_name, allow_none=True)
    return SectionResult(
        value=normalized_value,
        missing=normalized_value is None,
        data_quality=_build_optional_section_quality(
            section_name=section_name,
            status="missing" if normalized_value is None else "ok",
            error=None,
        ),
    )


def _ensure_dict(*, value: Any, section_name: str, allow_none: bool) -> DictStrAny | None:
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{section_name} must return a dictionary")

    if not isinstance(value, dict):
        raise TypeError(f"{section_name} must return a dictionary")

    return dict(value)


def _build_missing_sections(
    *,
    financial_summary: SectionResult,
    news_summary: SectionResult,
    breadth_context: SectionResult,
) -> list[str]:
    missing_sections: list[str] = []

    if financial_summary.missing:
        missing_sections.append("financial_summary")
    if news_summary.missing:
        missing_sections.append("news_summary")
    if breadth_context.missing:
        missing_sections.append("breadth_context")

    return missing_sections


def _build_data_quality(
    *,
    provider: TradePlanningProvider,
    company: DictStrAny,
    price_summary: DictStrAny,
    financial_summary: SectionResult,
    news_summary: SectionResult,
    breadth_context: SectionResult,
) -> DictStrAny:
    return {
        "provider_health": _safe_health_check(provider),
        "sections": {
            "company": _build_required_section_quality(section_name="company", value=company),
            "price_summary": _build_required_section_quality(
                section_name="price_summary",
                value=price_summary,
            ),
            "financial_summary": dict(financial_summary.data_quality),
            "news_summary": dict(news_summary.data_quality),
            "breadth_context": dict(breadth_context.data_quality),
        },
    }


def _safe_health_check(provider: TradePlanningProvider) -> DictStrAny:
    try:
        health = provider.health_check()
    except Exception as exc:
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    if not isinstance(health, dict):
        raise TypeError("health_check must return a dictionary")

    return dict(health)


def _build_required_section_quality(*, section_name: str, value: DictStrAny) -> DictStrAny:
    return {
        "section": section_name,
        "status": "ok",
        "present": True,
        "record_count": len(value),
    }


def _build_optional_section_quality(
    *,
    section_name: str,
    status: str,
    error: Exception | None,
) -> DictStrAny:
    quality: DictStrAny = {
        "section": section_name,
        "status": status,
        "present": status == "ok",
    }

    if error is not None:
        quality["error_type"] = type(error).__name__
        quality["error_message"] = str(error)

    return quality


def _build_provider_metadata(*, provider_name: str) -> DictStrAny:
    return {
        "provider_name": provider_name,
    }
