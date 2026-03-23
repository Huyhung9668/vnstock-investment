from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from models.report_manifest import ReportManifest


DictStrAny = dict[str, Any]


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
        run_date=datetime.utcnow(),
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
    manifest.validate()

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)
