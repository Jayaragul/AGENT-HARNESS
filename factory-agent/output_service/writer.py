from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from config.logging_config import get_logger
from guardrails.output_guard import OutputGuard
from output_service.csv_writer import write_csv
from output_service.excel_writer import write_excel
from output_service.json_writer import write_json
from output_service.output_registry import OutputRegistry

logger = get_logger("output_writer")


class Writer:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._registry = OutputRegistry(output_dir)

    def write_report(
        self,
        data: pd.DataFrame | list | dict,
        report_name: str,
        skill_name: str,
        source_datasets: list[str],
        query: str,
        result_summary: str = "",
        warnings: list[str] | None = None,
        fmt: str = "csv",
    ) -> Path:
        warnings = warnings or []
        audit_id = str(uuid4())[:8]

        ext = ".csv" if fmt == "csv" else ".xlsx" if fmt == "excel" else ".json"
        filename = f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = self._output_dir / filename

        OutputGuard.validate_output_path(filepath, self._output_dir)
        filepath = OutputGuard.check_no_overwrite(filepath)

        if fmt == "csv":
            if isinstance(data, pd.DataFrame):
                write_csv(data, filepath)
            elif isinstance(data, list):
                write_csv(pd.DataFrame(data), filepath)
            else:
                write_csv(pd.DataFrame([data]), filepath)
        elif fmt == "excel":
            if isinstance(data, pd.DataFrame):
                write_excel(data, filepath)
            elif isinstance(data, list):
                write_excel(pd.DataFrame(data), filepath)
            else:
                write_excel(pd.DataFrame([data]), filepath)
        elif fmt == "json":
            if isinstance(data, pd.DataFrame):
                write_json(data.to_dict(orient="records"), filepath)
            else:
                write_json(data, filepath)
        else:
            raise ValueError(f"Unsupported format: '{fmt}'")

        self._registry.register(
            report_name=report_name,
            file_path=filepath,
            skill_name=skill_name,
            query=query,
            result_summary=result_summary,
            source_datasets=source_datasets,
            warnings=warnings,
            audit_id=audit_id,
        )

        logger.info(
            "Report written",
            extra={
                "report_name": report_name,
                "file_path": str(filepath),
                "audit_id": audit_id,
            },
        )
        return filepath

    def get_registry(self) -> OutputRegistry:
        return self._registry
