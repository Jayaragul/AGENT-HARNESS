from __future__ import annotations

import os
from pathlib import Path


class PathSecurityError(Exception):
    pass


class PathGuard:
    @staticmethod
    def is_within_directory(target: Path, base_dir: Path) -> bool:
        try:
            target_resolved = os.path.normcase(str(target.resolve()))
            base_resolved = os.path.normcase(str(base_dir.resolve()))
            return os.path.commonpath([target_resolved, base_resolved]) == base_resolved
        except (OSError, ValueError):
            return False

    @staticmethod
    def has_path_traversal(path: Path) -> bool:
        path_str = str(path)
        return ".." in path_str.split("\\") or ".." in path_str.split("/")

    @staticmethod
    def has_suspicious_chars(path: Path) -> bool:
        path_str = str(path)
        dangerous = ["|", ";", "&", "`", "$", "(", ")", "{", "}", "<", ">", "!"]
        return any(c in path_str for c in dangerous)

    @staticmethod
    def validate_data_path(path: Path, data_dir: Path) -> Path:
        return PathGuard._validate_scoped_path(path, data_dir, "data")

    @staticmethod
    def validate_output_path(path: Path, output_dir: Path) -> Path:
        return PathGuard._validate_scoped_path(path, output_dir, "output")

    @staticmethod
    def _validate_scoped_path(path: Path, base_dir: Path, label: str) -> Path:
        if PathGuard.has_path_traversal(path):
            raise PathSecurityError(f"Path traversal detected: '{path}'")
        if not PathGuard.is_within_directory(path, base_dir):
            raise PathSecurityError(f"Path '{path}' is outside {label} directory")
        relative_path = path.resolve().relative_to(base_dir.resolve())
        if PathGuard.has_suspicious_chars(relative_path):
            raise PathSecurityError(f"Suspicious characters in path: '{path}'")
        return path
