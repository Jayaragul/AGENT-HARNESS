from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config.logging_config import get_logger

logger = get_logger("skill_registry")


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    display_name: str
    version: str
    description: str
    required_parameters: dict[str, dict[str, Any]]
    required_datasets: list[str]
    required_catalogs: list[str]
    handler_module: str
    handler_function: str
    allowed_tools: list[str]
    permissions: dict[str, Any]
    failure_behavior: str
    manifest_path: Path
    skill_md_path: Path | None = None

    @classmethod
    def from_manifest(cls, path: Path) -> "SkillDefinition":
        data = json.loads(path.read_text(encoding="utf-8"))
        skill_md_path = path.with_name("skill.md")
        return cls(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            required_parameters=data.get("required_parameters", {}),
            required_datasets=data.get("required_datasets", []),
            required_catalogs=data.get("required_catalogs", []),
            handler_module=data["handler_module"],
            handler_function=data["handler_function"],
            allowed_tools=data.get("allowed_tools", []),
            permissions=data.get("permissions", {}),
            failure_behavior=data.get("failure_behavior", ""),
            manifest_path=path,
            skill_md_path=skill_md_path if skill_md_path.exists() else None,
        )

    def to_skill_info(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "version": self.version,
            "description": self.description,
            "handler_module": self.handler_module,
            "handler_function": self.handler_function,
            "required_parameters": self.required_parameters,
            "required_datasets": self.required_datasets,
            "required_catalogs": self.required_catalogs,
            "allowed_tools": self.allowed_tools,
            "permissions": self.permissions,
            "failure_behavior": self.failure_behavior,
            "manifest_path": str(self.manifest_path),
            "skill_md_path": str(self.skill_md_path) if self.skill_md_path else None,
        }


class SkillRegistry:
    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._skills = self._load_skills()

    def _load_skills(self) -> dict[str, SkillDefinition]:
        skills: dict[str, SkillDefinition] = {}
        for manifest_path in sorted(self._skills_dir.glob("*/manifest.json")):
            definition = SkillDefinition.from_manifest(manifest_path)
            skills[definition.name] = definition

        logger.info(
            "Skill registry loaded",
            extra={"skills": sorted(skills.keys())},
        )
        return skills

    def get(self, skill_name: str) -> SkillDefinition | None:
        return self._skills.get(skill_name)

    def select(self, skill_name: str) -> dict[str, Any] | None:
        definition = self.get(skill_name)
        if definition is None:
            logger.warning(f"No skill found for intent: {skill_name}")
            return None
        return definition.to_skill_info()

    def list_skills(self) -> list[str]:
        return sorted(self._skills.keys())

    def all_catalogs(self) -> list[str]:
        catalogs: list[str] = []
        for definition in self._skills.values():
            catalogs.extend(definition.required_catalogs)
        return sorted(dict.fromkeys(catalogs))

    def all_datasets(self) -> list[str]:
        datasets: list[str] = []
        for definition in self._skills.values():
            datasets.extend(definition.required_datasets)
        return sorted(dict.fromkeys(datasets))

    def get_handler(self, skill_name: str) -> Callable[..., dict[str, Any]]:
        definition = self._skills[skill_name]
        module = importlib.import_module(definition.handler_module)
        handler = getattr(module, definition.handler_function)
        return handler
