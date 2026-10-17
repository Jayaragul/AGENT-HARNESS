from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_runtime_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep tests from mutating the repository's wiki, logs, or reports."""

    monkeypatch.setenv("WIKI_PATH", str(tmp_path / "wiki"))
    monkeypatch.setenv("LOG_PATH", str(tmp_path / "logs"))
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
