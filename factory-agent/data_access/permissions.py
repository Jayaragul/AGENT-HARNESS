from __future__ import annotations

from pathlib import Path


class PermissionError(Exception):
    pass


class Permissions:
    def __init__(self, data_dir: Path, output_dir: Path) -> None:
        self._data_dir = data_dir.resolve()
        self._output_dir = output_dir.resolve()

    def assert_read_only_data(self, path: Path) -> None:
        resolved = path.resolve()
        data_str = str(self._data_dir).lower()
        resolved_str = str(resolved).lower()
        if resolved_str.startswith(data_str):
            return
        raise PermissionError(f"Access denied: '{path}' is outside the data directory")

    def assert_output_path(self, path: Path) -> None:
        resolved = path.resolve()
        out_str = str(self._output_dir).lower()
        resolved_str = str(resolved).lower()
        if not resolved_str.startswith(out_str):
            raise PermissionError(
                f"Write denied: '{path}' is outside the output directory"
            )

    def assert_path_safe(self, path: Path) -> None:
        path_str = str(path)
        if ".." in path_str.split("\\") or ".." in path_str.split("/"):
            raise PermissionError(f"Suspicious path traversal: '{path}'")
        if any(c in path_str for c in ["|", ";", "&", "`", "$", "(", ")"]):
            raise PermissionError(f"Suspicious characters in path: '{path}'")
