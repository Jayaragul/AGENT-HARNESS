from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.intent_detector import Intent
from agent.skill_registry import SkillRegistry
from config.logging_config import get_logger

logger = get_logger("skill_selector")


class SkillSelector:
    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._registry = SkillRegistry(skills_dir)

    def select(self, intent: Intent) -> dict[str, Any] | None:
        skill_info = self._registry.select(intent.skill_name)
        if skill_info is None:
            return None
        logger.info(
            "Skill selected",
            extra={
                "skill": intent.skill_name,
                "datasets": skill_info["required_datasets"],
            },
        )
        return skill_info

    def get_handler(self, skill_name: str):
        return self._registry.get_handler(skill_name)

    def get_skill_md_path(self, skill_name: str) -> Path | None:
        skill_dir = self._skills_dir / skill_name
        md_path = skill_dir / "skill.md"
        if md_path.exists():
            return md_path
        return None

    def list_skills(self) -> list[str]:
        return self._registry.list_skills()

    def all_datasets(self) -> list[str]:
        return self._registry.all_datasets()

    def all_catalogs(self) -> list[str]:
        return self._registry.all_catalogs()
