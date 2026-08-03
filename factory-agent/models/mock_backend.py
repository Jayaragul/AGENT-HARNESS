from __future__ import annotations

from typing import Any

from models.base import LLMBackend, ModelConfig, ModelResponse


class MockBackend(LLMBackend):
    def __init__(self, config: ModelConfig | None = None) -> None:
        self._config = config or ModelConfig()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        return ModelResponse(
            content=f"[Mock response]\n"
            f"System prompt preview: {system_prompt[:100]}...\n"
            f"User query: {user_prompt[:100]}...\n"
            f"Context length: {len(context or '')} chars",
            model_name="mock",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )
