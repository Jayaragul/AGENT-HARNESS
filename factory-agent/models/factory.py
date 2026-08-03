from __future__ import annotations

from config.settings import BackendType, Settings
from models.base import LLMBackend, ModelConfig
from models.codex_backend import CodexBackend
from models.gemini_backend import GeminiBackend
from models.mock_backend import MockBackend


def create_backend(settings: Settings) -> LLMBackend:
    config = ModelConfig(temperature=0.0, max_tokens=2048)

    if settings.backend == BackendType.CODEX:
        return CodexBackend(api_key=settings.openai_api_key, config=config)
    elif settings.backend == BackendType.GEMINI:
        return GeminiBackend(api_key=settings.gemini_api_key, config=config)
    elif settings.backend == BackendType.MOCK:
        return MockBackend(config=config)
    else:
        raise ValueError(f"Unsupported backend: {settings.backend}")
