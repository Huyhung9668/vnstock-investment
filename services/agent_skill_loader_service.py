from __future__ import annotations

from pathlib import Path
from typing import Any

from services.agent_skill_runtime import SkillMetadata


def load_skill_metadata_map(skills_root: Path) -> dict[str, SkillMetadata]:
    metadata_map: dict[str, SkillMetadata] = {}
    if not skills_root.exists():
        return metadata_map

    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        metadata = _parse_skill_metadata(skill_file)
        metadata_map[skill_dir.name] = metadata
        metadata_map[metadata.name] = metadata
    return metadata_map


def _parse_skill_metadata(skill_file: Path) -> SkillMetadata:
    text = skill_file.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(text)
    name = str(frontmatter.get("name") or skill_file.parent.name).strip()
    description = str(frontmatter.get("description") or "").strip()
    return SkillMetadata(name=name, description=description, path=skill_file)


def _extract_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}
    payload: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload
