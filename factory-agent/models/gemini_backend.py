from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types as genai_types

from models.base import LLMBackend, ModelConfig, ModelResponse


class GeminiBackend(LLMBackend):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        config: ModelConfig | None = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._config = config or ModelConfig()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        full_prompt = f"{system_prompt}\n\n"
        if context:
            full_prompt += f"Context:\n{context}\n\n"
        full_prompt += f"User: {user_prompt}"

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=self._config.temperature,
                max_output_tokens=self._config.max_tokens,
            ),
        )
        return ModelResponse(
            content=response.text,
            model_name=self._model_name,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count
                if response.usage_metadata
                else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count
                if response.usage_metadata
                else 0,
            }
            if response.usage_metadata
            else None,
            raw=response,
        )
