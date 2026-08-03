import pytest

from config.settings import BackendType, Settings, ConfigurationError
from models.base import ModelConfig, ModelResponse
from models.gemini_backend import GeminiBackend
from models.factory import create_backend
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
