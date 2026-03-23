from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from models.report_manifest import ReportManifest


DictStrAny = dict[str, Any]
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def create_manifest(
    *,
    symbols: list[str],
    mode: str,
    source_used: str,
    files_created: list[str],
    warnings: list[str],
    errors: list[str],
    duration_seconds: float,
    data_quality_summary: DictStrAny,
) -> ReportManifest:
    return ReportManifest(
        run_id=str(uuid4()),
        run_date=datetime.now(VIETNAM_TZ),
        symbols=list(symbols),
        mode=mode,
        source_used=source_used,
        files_created=list(files_created),
        warnings=list(warnings),
        errors=list(errors),
        duration_seconds=float(duration_seconds),
        data_quality_summary=dict(data_quality_summary),
    )


def save_manifest(manifest: ReportManifest, output_path: str) -> str:
    if not isinstance(manifest, ReportManifest):
        raise TypeError("manifest must be a ReportManifest")
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError("output_path must be a non-empty string")

    manifest.validate()

    path = Path(output_path.strip())
    if path.exists() and path.is_dir():
        raise IsADirectoryError(f"output_path must be a file path, got directory: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)
