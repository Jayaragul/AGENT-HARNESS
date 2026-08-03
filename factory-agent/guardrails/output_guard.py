from __future__ import annotations

from pathlib import Path

from guardrails.path_guard import PathGuard


class OutputValidationError(Exception):
    pass


class OutputGuard:
    @staticmethod
    def validate_output_path(path: Path, output_dir: Path) -> None:
        PathGuard.validate_output_path(path, output_dir)

    @staticmethod
    def validate_report_metadata(metadata: dict) -> None:
        required = ["report_name", "created_timestamp", "skill_name", "query"]
        missing = [k for k in required if k not in metadata]
        if missing:
            raise OutputValidationError(f"Missing metadata fields: {missing}")

    @staticmethod
    def check_no_overwrite(path: Path) -> None:
        if path.exists():
            base = path.stem
            ext = path.suffix
            counter = 1
            while True:
                new_name = f"{base}_{counter}{ext}"
                new_path = path.with_name(new_name)
                if not new_path.exists():
                    return new_path
                counter += 1
        return path
