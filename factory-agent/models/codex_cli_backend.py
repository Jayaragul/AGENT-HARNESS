from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from models.base import LLMBackend, ModelConfig, ModelResponse


class CodexCliBackend(LLMBackend):
    """Use the locally authenticated Codex CLI as an isolated model agent.

    Each request runs in a fresh temporary directory with read-only sandboxing.
    The user's Codex login is used by the CLI; credentials are never read here.
    """

    def __init__(
        self,
        command: str = "codex",
        model_name: str = "",
        timeout_seconds: int = 180,
        config: ModelConfig | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._command = command
        self._model_name = model_name.strip()
        self._timeout_seconds = timeout_seconds
        self._config = config or ModelConfig()

    def _executable(self) -> str:
        # Prefer a native Windows executable over npm's .cmd/.ps1 shims because
        # subprocess can launch the executable directly without a shell.
        if os.name == "nt" and self._command == "codex":
            native = shutil.which("codex.exe")
            if native:
                return native
        executable = shutil.which(self._command)
        if executable:
            return executable
        candidate = Path(self._command)
        if candidate.is_file():
            return str(candidate.resolve())
        raise RuntimeError(
            f"Codex CLI executable '{self._command}' was not found. "
            "Install Codex CLI or set CODEX_CLI_COMMAND to its executable path."
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        prompt_sections = [
            (
                "You are providing a response to a factory operations agent harness. "
                "Do not modify files or perform actions; return only the requested "
                "answer for the calling application."
            ),
            f"System instructions:\n{system_prompt}",
        ]
        if context:
            prompt_sections.append(f"Context:\n{context}")
        prompt_sections.append(f"User request:\n{user_prompt}")
        prompt = "\n\n".join(prompt_sections)

        executable = self._executable()
        with tempfile.TemporaryDirectory(prefix="factory-agent-codex-") as workdir:
            output_path = Path(workdir) / "answer.txt"
            command = [
                executable,
                "exec",
                "--json",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--cd",
                workdir,
                "--output-last-message",
                str(output_path),
            ]
            if self._model_name:
                command.extend(["--model", self._model_name])
            command.append("-")

            try:
                result = subprocess.run(
                    command,
                    input=prompt,
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self._timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"Codex CLI did not finish within {self._timeout_seconds} seconds."
                ) from exc
            except OSError as exc:
                raise RuntimeError(f"Could not start Codex CLI: {exc}") from exc

            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                if len(detail) > 2000:
                    detail = detail[-2000:]
                raise RuntimeError(
                    "Codex CLI request failed"
                    + (f": {detail}" if detail else f" (exit code {result.returncode})")
                )
            if not output_path.is_file():
                raise RuntimeError(
                    "Codex CLI completed without writing its final response."
                )
            content = output_path.read_text(encoding="utf-8").strip()
            if not content:
                raise RuntimeError("Codex CLI returned an empty response.")

        return ModelResponse(
            content=content,
            model_name=self._model_name or "codex-cli-default",
            raw={"backend": "codex_cli", "sandbox": "read-only", "ephemeral": True},
        )
