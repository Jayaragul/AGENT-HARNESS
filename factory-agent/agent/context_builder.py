from __future__ import annotations

from pathlib import Path
from typing import Any


class ContextBuilder:
    def __init__(self, catalog_dir: Path) -> None:
        self._catalog_dir = catalog_dir

    def load_catalog(self, catalog_name: str) -> str:
        path = self._catalog_dir / catalog_name
        if not path.exists():
            return f"# Catalog '{catalog_name}' not found."
        return path.read_text(encoding="utf-8")

    def build_context(
        self,
        skill_info: dict[str, Any],
        intent: Any,
    ) -> str:
        parts: list[str] = []
        parts.append("# Data Catalogs\n")

        for catalog_name in skill_info.get("required_catalogs", []):
            catalog_content = self.load_catalog(catalog_name)
            parts.append(catalog_content)
            parts.append("\n---\n")

        return "\n".join(parts)
