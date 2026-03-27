from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


DictStrAny = dict[str, Any]


@dataclass(slots=True)
class SkillMetadata:
    name: str
    description: str
    path: Path | None = None


@dataclass(slots=True)
class AgentSkill:
    skill_id: str
    metadata: SkillMetadata
    handler: Callable[["AgentRuntimeContext"], DictStrAny]
    depends_on: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AgentStepResult:
    skill_id: str
    status: str
    summary: str
    payload: DictStrAny = field(default_factory=dict)


@dataclass(slots=True)
class AgentRuntimeContext:
    project_root: Path
    objective: str
    config_dir: Path
    ai_mode: str
    send_telegram: bool
    export_reports: bool
    runtime_bundle: Any | None = None
    run_context: Any | None = None
    data: DictStrAny = field(default_factory=dict)
    step_results: list[AgentStepResult] = field(default_factory=list)

    def set_data(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def add_step_result(self, result: AgentStepResult) -> None:
        self.step_results.append(result)
