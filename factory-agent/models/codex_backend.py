from __future__ import annotations

from typing import Any

from openai import OpenAI

from models.base import LLMBackend, ModelConfig, ModelResponse


class CodexBackend(LLMBackend):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        config: ModelConfig | None = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name
        self._config = config or ModelConfig()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return ModelResponse(
            content=choice.message.content or "",
            model_name=self._model_name,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            } if response.usage else None,
            raw=response,
        )
