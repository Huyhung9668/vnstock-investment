from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_market_overview
import daily_run
import universe_scan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full trading terminal pipeline: universe scan, market overview, daily run, AI overlay, and report export.",
    )
    parser.add_argument(
        "--config-dir",
        default=str(PROJECT_ROOT / "config"),
        help="Directory containing runtime.yaml, sources.yaml, watchlist.yaml and optional universe.yaml.",
    )
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Skip universe scan and reuse existing derived data.",
    )
    parser.add_argument(
        "--skip-overview",
        action="store_true",
        help="Skip rebuilding market overview.",
    )
    parser.add_argument(
        "--ai-mode",
        choices=["api", "file", "local", "off"],
        default="api",
        help="AI overlay mode. Default: api.",
    )
    parser.add_argument(
        "--openai-model",
        default=None,
        help="Override OPENAI_MODEL for the run.",
    )
    parser.add_argument(
        "--openai-base-url",
        default=None,
        help="Override OPENAI_BASE_URL for the run.",
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Path to AI prompt file when using file mode.",
    )
    parser.add_argument(
        "--response-file",
        default=None,
        help="Path to AI response file when using file mode.",
    )
    return parser.parse_args()


def _set_env_if_value(name: str, value: str | None) -> None:
    if value is not None and str(value).strip():
        os.environ[name] = str(value).strip()


def _configure_ai(args: argparse.Namespace) -> list[str]:
    notes: list[str] = []
    if args.ai_mode == "off":
        os.environ["AI_ANALYSIS_ENABLED"] = "false"
        notes.append("AI overlay disabled.")
        return notes

    os.environ["AI_ANALYSIS_ENABLED"] = "true"
    os.environ["AI_ANALYSIS_MODE"] = args.ai_mode
    _set_env_if_value("OPENAI_MODEL", args.openai_model)
    _set_env_if_value("OPENAI_BASE_URL", args.openai_base_url)

    if args.ai_mode == "file":
        prompt_file = args.prompt_file or str(PROJECT_ROOT / "artifacts" / "ai_prompt.json")
        response_file = args.response_file or str(PROJECT_ROOT / "artifacts" / "ai_response.json")
        os.environ["AI_ANALYSIS_PROMPT_FILE"] = prompt_file
        os.environ["AI_ANALYSIS_RESPONSE_FILE"] = response_file
        notes.append(f"AI file bridge enabled. prompt={prompt_file}")
        notes.append(f"AI file bridge enabled. response={response_file}")
        return notes

    if args.ai_mode == "local":
        if not os.getenv("OPENAI_BASE_URL", "").strip():
            os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
        if not os.getenv("OPENAI_MODEL", "").strip():
            os.environ["OPENAI_MODEL"] = "qwen2.5:14b"
        notes.append(
            f"AI local mode enabled with model={os.getenv('OPENAI_MODEL')} base_url={os.getenv('OPENAI_BASE_URL')}."
        )
        notes.append("Local mode works with Ollama/OpenAI-compatible local servers and does not require a cloud API key.")
        return notes

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        notes.append("AI api mode requested but OPENAI_API_KEY is missing; pipeline will continue without AI overlay.")
    else:
        notes.append(f"AI api mode enabled with model={os.getenv('OPENAI_MODEL', 'default')}.")
    return notes


def _run_universe_scan(skip_scan: bool) -> str:
    if skip_scan:
        return "Universe scan skipped."
    universe_scan.main()
    return "Universe scan completed."


def _run_market_overview(skip_overview: bool) -> str:
    if skip_overview:
        return "Market overview rebuild skipped."
    build_market_overview.main()
    return "Market overview rebuild completed."


def _run_daily(config_dir: str) -> dict[str, Any]:
    original_parse_args = daily_run.parse_args
    try:
        daily_run.parse_args = lambda: type("Args", (), {"config_dir": config_dir})()
        return daily_run.main()
    finally:
        daily_run.parse_args = original_parse_args


def main() -> int:
    args = parse_args()
    daily_run.load_dotenv_if_present()

    ai_notes = _configure_ai(args)
    progress_notes = []
    progress_notes.append(_run_universe_scan(args.skip_scan))
    progress_notes.append(_run_market_overview(args.skip_overview))
    summary = _run_daily(args.config_dir)

    print("TRADING TERMINAL RUN")
    for note in [*ai_notes, *progress_notes]:
        print(f"- {note}")
    print(f"- run_id={summary.get('run_id')}")
    print(f"- terminal_mode={summary.get('terminal_mode')}")
    print(f"- headline={summary.get('headline')}")
    print(f"- output_dir={summary.get('artifacts_output_dir')}")
    print(f"- manifest_path={summary.get('manifest_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
