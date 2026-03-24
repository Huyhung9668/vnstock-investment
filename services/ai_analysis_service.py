from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests


DictStrAny = dict[str, Any]


@dataclass(frozen=True, slots=True)
class AIAnalysisConfig:
    enabled: bool
    mode: str
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: int
    prompt_file: str | None
    response_file: str | None


def load_ai_analysis_config() -> AIAnalysisConfig:
    enabled = _env_bool("AI_ANALYSIS_ENABLED", default=False)
    mode = (_env_str("AI_ANALYSIS_MODE") or "api").strip().lower()
    api_key = _env_str("OPENAI_API_KEY")
    base_url = _env_str("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = _env_str("OPENAI_MODEL") or "gpt-4.1-mini"
    timeout_seconds = _env_int("OPENAI_TIMEOUT_SECONDS", default=45)
    prompt_file = _env_str("AI_ANALYSIS_PROMPT_FILE")
    response_file = _env_str("AI_ANALYSIS_RESPONSE_FILE")
    return AIAnalysisConfig(
        enabled=enabled,
        mode=mode,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        timeout_seconds=max(timeout_seconds, 10),
        prompt_file=prompt_file,
        response_file=response_file,
    )


def ai_analysis_ready(config: AIAnalysisConfig) -> bool:
    if not config.enabled or not config.model:
        return False
    if config.mode == "file":
        return bool(config.response_file)
    return bool(config.api_key and config.base_url)


def build_ai_daily_briefing(
    *,
    config: AIAnalysisConfig,
    base_briefing: dict[str, Any],
    market_overview: dict[str, Any] | None,
    symbol_payloads: dict[str, dict[str, Any]] | None,
    trade_plan_payloads: dict[str, dict[str, Any]] | None,
    warnings: list[str] | None,
) -> DictStrAny:
    if not ai_analysis_ready(config):
        raise ValueError("AI analysis is not configured.")

    response_payload = _chat_completion(
        config=config,
        system_prompt=_system_prompt(),
        user_prompt=_user_prompt(
            base_briefing=base_briefing,
            market_overview=market_overview or {},
            symbol_payloads=symbol_payloads or {},
            trade_plan_payloads=trade_plan_payloads or {},
            warnings=warnings or [],
        ),
    )
    normalized = _parse_json_payload(response_payload)
    normalized["model"] = config.model
    normalized["provider"] = config.base_url
    return normalized


def _chat_completion(*, config: AIAnalysisConfig, system_prompt: str, user_prompt: str) -> str:
    if config.mode == "file":
        return _file_completion(
            config=config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    response = requests.post(
        f"{config.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("AI response did not include choices.")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("AI response content was empty.")
    return content


def _file_completion(*, config: AIAnalysisConfig, system_prompt: str, user_prompt: str) -> str:
    response_file = config.response_file
    if not response_file:
        raise ValueError("AI_ANALYSIS_RESPONSE_FILE is required when AI_ANALYSIS_MODE=file.")

    request_payload = {
        "mode": config.mode,
        "model": config.model,
        "provider": "local_file_bridge",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "expected_schema": {
            "headline": "string",
            "market_story": "string",
            "portfolio_focus": "string",
            "top_symbol_notes": [{"symbol": "string", "note": "string"}],
            "action_plan": ["string"],
            "risk_alerts": ["string"],
        },
    }

    if config.prompt_file:
        with open(config.prompt_file, "w", encoding="utf-8") as handle:
            json.dump(request_payload, handle, ensure_ascii=False, indent=2)

    with open(response_file, encoding="utf-8") as handle:
        content = handle.read().strip()

    if not content:
        raise ValueError("AI analysis response file was empty.")
    return content


def _system_prompt() -> str:
    return (
        "Ban la AI investment copilot cho daily pipeline. "
        "Nhiem vu la bien du lieu co san thanh insight ro rang, ngan gon, co hanh dong. "
        "Chi duoc dua tren du lieu da cung cap, khong du doan them. "
        "Tra ve JSON object hop le voi cac key: "
        "headline, market_story, portfolio_focus, top_symbol_notes, action_plan, risk_alerts. "
        "top_symbol_notes va action_plan va risk_alerts phai la array. "
        "Moi top_symbol_notes item phai la object co key symbol va note."
    )


def _user_prompt(
    *,
    base_briefing: dict[str, Any],
    market_overview: dict[str, Any],
    symbol_payloads: dict[str, dict[str, Any]],
    trade_plan_payloads: dict[str, dict[str, Any]],
    warnings: list[str],
) -> str:
    compact_payload = {
        "base_briefing": base_briefing,
        "market_overview": market_overview,
        "symbols": symbol_payloads,
        "trade_plans": trade_plan_payloads,
        "warnings": warnings[:12],
    }
    return (
        "Phan tich payload duoi day va viet lai thanh insight co nguc canh cho trader VN. "
        "Uu tien chi ra 1) boi canh thi truong, 2) ma dang dang chu y nhat, 3) hanh dong tiep theo, 4) canh bao. "
        "Neu du lieu degraded thi phai noi ro. "
        "Payload JSON:\n"
        f"{json.dumps(compact_payload, ensure_ascii=False)}"
    )


def _parse_json_payload(content: str) -> DictStrAny:
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object.")

    top_symbol_notes = payload.get("top_symbol_notes")
    if not isinstance(top_symbol_notes, list):
        top_symbol_notes = []

    normalized_notes: list[DictStrAny] = []
    for item in top_symbol_notes[:5]:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        note = str(item.get("note", "")).strip()
        if symbol and note:
            normalized_notes.append({"symbol": symbol, "note": note})

    return {
        "headline": str(payload.get("headline", "")).strip(),
        "market_story": str(payload.get("market_story", "")).strip(),
        "portfolio_focus": str(payload.get("portfolio_focus", "")).strip(),
        "top_symbol_notes": normalized_notes,
        "action_plan": _normalize_string_list(payload.get("action_plan")),
        "risk_alerts": _normalize_string_list(payload.get("risk_alerts")),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default
