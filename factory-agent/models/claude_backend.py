from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from models.base import LLMBackend, ModelConfig, ModelResponse


class ClaudeBackend(LLMBackend):
    """Anthropic adapter implementing the same text-generation contract as peers."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-sonnet-4-6",
        config: ModelConfig | None = None,
    ) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model_name = model_name
        self._config = config or ModelConfig()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        prompt = f"Context:\n{context}\n\n{user_prompt}" if context else user_prompt
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=self._config.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        content = "\n".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(response, "usage", None)
        return ModelResponse(
            content=content,
            model_name=self._model_name,
            usage={
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
            } if usage else None,
            raw=response,
        )
