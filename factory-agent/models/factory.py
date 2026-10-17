from __future__ import annotations

from config.settings import BackendType, Settings
from models.base import LLMBackend, ModelConfig


def create_backend(settings: Settings) -> LLMBackend:
    config = ModelConfig(temperature=0.0, max_tokens=2048)

    if settings.backend == BackendType.CODEX:
        from models.codex_backend import CodexBackend

        return CodexBackend(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            config=config,
        )
    elif settings.backend == BackendType.CODEX_CLI:
        from models.codex_cli_backend import CodexCliBackend

        return CodexCliBackend(
            command=settings.codex_cli_command,
            model_name=settings.codex_cli_model,
            timeout_seconds=settings.codex_cli_timeout_seconds,
            config=config,
        )
    elif settings.backend == BackendType.GEMINI:
        from models.gemini_backend import GeminiBackend

        return GeminiBackend(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
            config=config,
        )
    elif settings.backend == BackendType.CLAUDE:
        from models.claude_backend import ClaudeBackend

        return ClaudeBackend(
            api_key=settings.anthropic_api_key,
            model_name=settings.claude_model,
            config=config,
        )
    elif settings.backend == BackendType.OLLAMA:
        from models.ollama_backend import OllamaBackend

        return OllamaBackend(
            host=settings.ollama_host,
            model_name=settings.ollama_model,
            config=config,
        )
    elif settings.backend == BackendType.MOCK:
        from models.mock_backend import MockBackend

        return MockBackend(config=config)
    else:
        raise ValueError(f"Unsupported backend: {settings.backend}")
