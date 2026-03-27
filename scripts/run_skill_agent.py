from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from services.agent_skill_registry_service import build_agent_execution_package, save_agent_runtime_artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VNStock as a skill-based agent runtime.")
    parser.add_argument("--objective", default="Phân tích thị trường, chọn top 5 LONG và tạo kế hoạch hành động.")
    parser.add_argument("--config-dir", default=str(PROJECT_ROOT / "config" / "test50"))
    parser.add_argument("--ai-mode", choices=["off", "local", "file", "api"], default="off")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--no-export", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_agent_execution_package(
        project_root=PROJECT_ROOT,
        objective=args.objective,
        config_dir=Path(args.config_dir).resolve(),
        ai_mode=args.ai_mode,
        send_telegram=args.send_telegram,
        export_reports=not args.no_export,
    )
    execution = dict(payload.get("execution") or {})
    run_id = _extract_run_id(execution)
    artifact_path = save_agent_runtime_artifact(project_root=PROJECT_ROOT, run_id=run_id, payload=payload)

    print("SKILL AGENT RUNTIME")
    _safe_print(f"- objective={args.objective}")
    _safe_print(f"- config_dir={Path(args.config_dir).resolve()}")
    _safe_print(f"- run_id={run_id}")
    _safe_print(f"- final_summary={execution.get('final_summary')}")
    _safe_print(f"- artifacts_output_dir={execution.get('artifacts_output_dir')}")
    _safe_print(f"- manifest_path={execution.get('manifest_path')}")
    _safe_print(f"- agent_runtime_artifact={artifact_path}")
    _safe_print(json.dumps(payload.get("planner") or {}, ensure_ascii=False, indent=2))
    return 0


def _extract_run_id(execution: dict[str, object]) -> str:
    manifest_path = str(execution.get("manifest_path") or "").strip()
    if manifest_path:
        parts = Path(manifest_path).parts
        for part in parts:
            if part.startswith("202"):
                return part
    return "agent_runtime"


def _safe_print(text: object) -> None:
    message = str(text)
    try:
        print(message)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(message.encode("utf-8", errors="replace") + b"\n")


if __name__ == "__main__":
    raise SystemExit(main())
