from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ai_analysis_service import (
    ai_analysis_ready,
    build_ai_daily_briefing,
    load_ai_analysis_config,
)


def test_file_mode_reads_local_response_and_dumps_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    prompt_file = tmp_path / "ai_prompt.json"
    response_file = tmp_path / "ai_response.json"
    response_file.write_text(
        json.dumps(
            {
                "headline": "Thi truong di ngang",
                "market_story": "Dong tien chua mo rong.",
                "portfolio_focus": "Tap trung quan tri rui ro.",
                "top_symbol_notes": [{"symbol": "FPT", "note": "Giu nen gia tot."}],
                "action_plan": ["Theo doi phan ung gia quanh ho tro."],
                "risk_alerts": ["Thanh khoan chua xac nhan."],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("AI_ANALYSIS_MODE", "file")
    monkeypatch.setenv("OPENAI_MODEL", "codex-local-bridge")
    monkeypatch.setenv("AI_ANALYSIS_PROMPT_FILE", str(prompt_file))
    monkeypatch.setenv("AI_ANALYSIS_RESPONSE_FILE", str(response_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = load_ai_analysis_config()
    payload = build_ai_daily_briefing(
        config=config,
        base_briefing={"headline": "Base"},
        market_overview={"trend": "sideways"},
        symbol_payloads={"FPT": {"score": 85}},
        trade_plan_payloads={"FPT": {"bias": "neutral"}},
        warnings=["degraded data"],
    )

    assert payload["headline"] == "Thi truong di ngang"
    assert payload["model"] == "codex-local-bridge"
    assert payload["top_symbol_notes"] == [{"symbol": "FPT", "note": "Giu nen gia tot."}]

    prompt_payload = json.loads(prompt_file.read_text(encoding="utf-8"))
    assert prompt_payload["provider"] == "local_file_bridge"
    assert prompt_payload["model"] == "codex-local-bridge"
    assert "base_briefing" in prompt_payload["user_prompt"]


def test_local_mode_is_ready_without_cloud_api_key(monkeypatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("AI_ANALYSIS_MODE", "local")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen2.5:14b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = load_ai_analysis_config()

    assert config.mode == "local"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.model == "qwen2.5:14b"
    assert ai_analysis_ready(config) is True


def test_default_ai_mode_prefers_local_when_not_overridden(monkeypatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_ENABLED", "true")
    monkeypatch.delenv("AI_ANALYSIS_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    config = load_ai_analysis_config()

    assert config.mode == "local"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.model == "qwen2.5:14b"
