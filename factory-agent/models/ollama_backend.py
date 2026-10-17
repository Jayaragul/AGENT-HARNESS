from __future__ import annotations

from typing import Any

import httpx

from models.base import LLMBackend, ModelConfig, ModelResponse


class OllamaBackend(LLMBackend):
    """Local Ollama adapter using its HTTP chat endpoint (no hosted API key)."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model_name: str = "qwen3.5:9b",
        config: ModelConfig | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._host = host.rstrip("/")
        self._model_name = model_name
        self._config = config or ModelConfig()
        self._client = httpx.Client(base_url=self._host, timeout=timeout)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        user_content = f"Context:\n{context}\n\n{user_prompt}" if context else user_prompt
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._model_name,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "options": {
                    "temperature": self._config.temperature,
                    "num_predict": self._config.max_tokens,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message") or {}
        prompt_tokens = payload.get("prompt_eval_count")
        completion_tokens = payload.get("eval_count")
        usage = None
        if prompt_tokens is not None or completion_tokens is not None:
            usage = {}
            if prompt_tokens is not None:
                usage["prompt_tokens"] = int(prompt_tokens)
            if completion_tokens is not None:
                usage["completion_tokens"] = int(completion_tokens)
        return ModelResponse(
            content=message.get("content") or "",
            model_name=payload.get("model", self._model_name),
            usage=usage,
            raw=payload,
        )

    def close(self) -> None:
        self._client.close()
