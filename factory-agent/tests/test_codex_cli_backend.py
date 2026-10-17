from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from models.codex_cli_backend import CodexCliBackend


def test_codex_cli_backend_uses_isolated_read_only_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text('{"decision":"unsupported"}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="{}\n", stderr="")

    monkeypatch.setattr("models.codex_cli_backend.shutil.which", lambda _: "codex.exe")
    monkeypatch.setattr("models.codex_cli_backend.subprocess.run", fake_run)

    response = CodexCliBackend(model_name="codex-test").generate(
        "Use JSON.", "What is available?", context="Catalog: empty"
    )

    command = captured["command"]
    kwargs = captured["kwargs"]
    assert isinstance(command, list)
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--model") + 1] == "codex-test"
    assert "Catalog: empty" in kwargs["input"]
    assert "What is available?" in kwargs["input"]
    assert Path(kwargs["cwd"]).name.startswith("factory-agent-codex-")
    assert response.content == '{"decision":"unsupported"}'
    assert response.model_name == "codex-test"


def test_codex_cli_backend_reports_missing_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("models.codex_cli_backend.shutil.which", lambda _: None)
    backend = CodexCliBackend(command="missing-codex")

    with pytest.raises(RuntimeError, match="was not found"):
        backend.generate("system", "user")


def test_codex_cli_backend_reports_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("models.codex_cli_backend.shutil.which", lambda _: "codex")
    monkeypatch.setattr(
        "models.codex_cli_backend.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, stdout="", stderr="Sign in to Codex"
        ),
    )

    with pytest.raises(RuntimeError, match="Sign in to Codex"):
        CodexCliBackend().generate("system", "user")
