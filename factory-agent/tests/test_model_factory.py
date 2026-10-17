import importlib
import sys
from types import SimpleNamespace

import pytest

from config.settings import BackendType, ConfigurationError, Settings
from models.base import ModelConfig, ModelResponse
from models.factory import create_backend
from models.gemini_backend import GeminiBackend
from models.mock_backend import MockBackend


class _FakeUsageMetadata:
    prompt_token_count = 3
    candidates_token_count = 7


class _FakeGeminiResponse:
    text = "fake response"
    usage_metadata = _FakeUsageMetadata()


class _FakeGeminiModels:
    def __init__(self) -> None:
        self.last_model = None
        self.last_contents = None

    def generate_content(self, model: str, contents: str, config) -> _FakeGeminiResponse:
        self.last_model = model
        self.last_contents = contents
        return _FakeGeminiResponse()


class _FakeGeminiClient:
    def __init__(self) -> None:
        self.models = _FakeGeminiModels()


def test_mock_backend_creation() -> None:
    settings = Settings(backend=BackendType.MOCK)
    backend = create_backend(settings)
    assert isinstance(backend, MockBackend)


def test_codex_cli_backend_creation_needs_no_api_key() -> None:
    settings = Settings(backend=BackendType.CODEX_CLI, openai_api_key="")
    settings.validate_backend_keys()

    from models.codex_cli_backend import CodexCliBackend

    assert isinstance(create_backend(settings), CodexCliBackend)


def test_mock_backend_generates_response() -> None:
    backend = MockBackend()
    response = backend.generate(
        system_prompt="You are a helper",
        user_prompt="What is 2+2?",
    )
    assert isinstance(response, ModelResponse)
    assert "Mock response" in response.content
    assert response.model_name == "mock"


def test_model_config_defaults() -> None:
    config = ModelConfig()
    assert config.temperature == 0.0
    assert config.max_tokens == 2048


def test_model_config_custom() -> None:
    config = ModelConfig(temperature=0.5, max_tokens=100)
    assert config.temperature == 0.5
    assert config.max_tokens == 100


def test_codex_backend_missing_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    settings = Settings(backend=BackendType.CODEX)
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        settings.validate_backend_keys()


def test_gemini_backend_missing_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")
    settings = Settings(backend=BackendType.GEMINI)
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY"):
        settings.validate_backend_keys()


def test_claude_backend_missing_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    settings = Settings(backend=BackendType.CLAUDE)
    with pytest.raises(ConfigurationError, match="ANTHROPIC_API_KEY"):
        settings.validate_backend_keys()


def test_provider_defaults_are_configurable() -> None:
    settings = Settings(
        backend=BackendType.CLAUDE,
        anthropic_api_key="test-key",
        claude_model="claude-sonnet-custom",
    )
    assert settings.claude_model == "claude-sonnet-custom"


def test_backend_selection_is_lazy_for_sdk() -> None:
    backend = create_backend(Settings(backend=BackendType.MOCK))
    assert isinstance(backend, MockBackend)


def test_ollama_backend_requires_no_api_key():
    settings = Settings(backend=BackendType.OLLAMA)
    settings.validate_backend_keys()


def test_ollama_backend_normalizes_chat_response():
    from models.ollama_backend import OllamaBackend

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "qwen3.5:9b",
                "message": {"role": "assistant", "content": '{"decision":"unsupported"}'},
                "prompt_eval_count": 12,
                "eval_count": 5,
            }

    class FakeClient:
        def __init__(self):
            self.request = None

        def post(self, path, json):
            self.request = (path, json)
            return FakeResponse()

        def close(self):
            return None

    backend = OllamaBackend(host="http://ollama.test", model_name="qwen3.5:9b")
    fake_client = FakeClient()
    backend._client.close()
    backend._client = fake_client

    response = backend.generate("rules", "question", context="catalog")

    path, request = fake_client.request
    assert path == "/api/chat"
    assert request["stream"] is False
    assert request["messages"][0] == {"role": "system", "content": "rules"}
    assert "catalog" in request["messages"][1]["content"]
    assert response.content == '{"decision":"unsupported"}'
    assert response.usage == {"prompt_tokens": 12, "completion_tokens": 5}


def test_claude_adapter_normalizes_messages_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMessages:
        def __init__(self):
            self.request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text='{"decision":"unsupported"}')],
                usage=SimpleNamespace(input_tokens=11, output_tokens=4),
            )

    messages = FakeMessages()
    monkeypatch.setitem(
        sys.modules,
        "anthropic",
        SimpleNamespace(Anthropic=lambda **kwargs: SimpleNamespace(messages=messages)),
    )
    sys.modules.pop("models.claude_backend", None)
    ClaudeBackend = importlib.import_module("models.claude_backend").ClaudeBackend
    backend = ClaudeBackend(api_key="test-key", model_name="claude-test")

    response = backend.generate("system rules", "user question", context="catalog")

    assert messages.request["model"] == "claude-test"
    assert messages.request["system"] == "system rules"
    assert "catalog" in messages.request["messages"][0]["content"]
    assert response.content == '{"decision":"unsupported"}'
    assert response.usage == {"prompt_tokens": 11, "completion_tokens": 4}


def test_mock_backend_no_key_required() -> None:
    settings = Settings(backend=BackendType.MOCK)
    settings.validate_backend_keys()


def test_gemini_backend_uses_updated_model_name() -> None:
    backend = GeminiBackend(api_key="dummy-key")
    fake_client = _FakeGeminiClient()
    backend._client = fake_client

    response = backend.generate(
        system_prompt="You are a helper",
        user_prompt="What is 2+2?",
    )

    assert fake_client.models.last_model == "gemini-2.5-flash"
    assert isinstance(response, ModelResponse)
    assert response.content == "fake response"
