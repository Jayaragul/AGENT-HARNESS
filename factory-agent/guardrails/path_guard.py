from __future__ import annotations

from pathlib import Path


class PathSecurityError(Exception):
    pass


class PathGuard:
    @staticmethod
    def is_within_directory(target: Path, base_dir: Path) -> bool:
        try:
            target_resolved = target.resolve()
            base_resolved = base_dir.resolve()
            return str(target_resolved).lower().startswith(str(base_resolved).lower())
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
        if PathGuard.has_path_traversal(path):
            raise PathSecurityError(f"Path traversal detected: '{path}'")
        if PathGuard.has_suspicious_chars(path):
            raise PathSecurityError(f"Suspicious characters in path: '{path}'")
        if not PathGuard.is_within_directory(path, data_dir):
            raise PathSecurityError(f"Path '{path}' is outside data directory")
        return path

    @staticmethod
    def validate_output_path(path: Path, output_dir: Path) -> Path:
        if PathGuard.has_path_traversal(path):
            raise PathSecurityError(f"Path traversal detected: '{path}'")
        if PathGuard.has_suspicious_chars(path):
            raise PathSecurityError(f"Suspicious characters in path: '{path}'")
        if not PathGuard.is_within_directory(path, output_dir):
            raise PathSecurityError(f"Path '{path}' is outside output directory")
        return path
