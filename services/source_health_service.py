from __future__ import annotations

from pathlib import Path
from typing import Any

import os


DictStrAny = dict[str, Any]


def check_source_health(
    *,
    project_root: Path,
    runtime_config: dict[str, Any] | None,
    sources_config: dict[str, Any] | None,
) -> DictStrAny:
    runtime = dict(runtime_config or {})
    sources = dict(sources_config or {})

    derived_dir = project_root / "data" / "derived"
    checks = {
        "config_runtime": True,
        "config_sources": True,
        "derived_dir_exists": derived_dir.exists(),
        "top10_exists": (derived_dir / "top10_symbols.json").exists(),
        "ranking_exists": (derived_dir / "universe_scores.csv").exists(),
        "market_overview_exists": (derived_dir / "market_overview.json").exists(),
        "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY", "").strip()),
    }

    providers = dict(sources.get("providers") or {})
    primary_provider = str(providers.get("primary", "")).strip().lower() or "unknown"
    fallback_provider = str(providers.get("fallback", "")).strip().lower() or None
    feature_flags = dict(runtime.get("features") or {})

    warnings: list[str] = []
    if not checks["derived_dir_exists"]:
        warnings.append("data/derived chua ton tai; can chay ingestion stage.")
    if feature_flags.get("market_overview", False) and not checks["market_overview_exists"]:
        warnings.append("market_overview feature bat nhung chua co market_overview.json.")
    if not checks["ranking_exists"]:
        warnings.append("Chua co universe_scores.csv.")
    if os.getenv("AI_ANALYSIS_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"} and not checks["openai_api_key_present"]:
        warnings.append("AI_ANALYSIS_ENABLED bat nhung OPENAI_API_KEY chua co.")

    status = "ready" if not warnings else "degraded"
    return {
        "status": status,
        "primary_provider": primary_provider,
        "fallback_provider": fallback_provider,
        "checks": checks,
        "warnings": warnings,
    }
