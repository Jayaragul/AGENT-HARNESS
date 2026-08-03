from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class OutputRegistry:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._entries: list[dict[str, Any]] = []

    def register(
        self,
        report_name: str,
        file_path: Path,
        skill_name: str,
        query: str,
        result_summary: str,
        source_datasets: list[str],
        warnings: list[str],
        audit_id: str,
    ) -> dict[str, Any]:
        entry = {
            "report_name": report_name,
            "file_path": str(file_path),
            "created_timestamp": datetime.now().isoformat(),
            "skill_name": skill_name,
            "query": query,
            "result_summary": result_summary,
            "source_datasets": source_datasets,
            "warnings": warnings,
            "audit_id": audit_id,
        }
        self._entries.append(entry)
        return entry

    def list_outputs(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def get_output_dir(self) -> Path:
        return self._output_dir
