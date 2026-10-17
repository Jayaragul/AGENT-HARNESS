from __future__ import annotations

from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()

APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parent


class BackendType(str, Enum):
    CODEX = "CODEX"
    CODEX_CLI = "CODEX_CLI"
    GEMINI = "GEMINI"
    CLAUDE = "CLAUDE"
    OLLAMA = "OLLAMA"
    MOCK = "MOCK"


class Settings(BaseSettings):
    backend: BackendType = BackendType.CODEX_CLI
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    openai_model: str = Field(default="gpt-5.1-codex", validation_alias="OPENAI_MODEL")
    codex_cli_command: str = Field(default="codex", validation_alias="CODEX_CLI_COMMAND")
    codex_cli_model: str = Field(default="", validation_alias="CODEX_CLI_MODEL")
    codex_cli_timeout_seconds: int = Field(
        default=180, validation_alias="CODEX_CLI_TIMEOUT_SECONDS"
    )
    gemini_model: str = Field(
        default="gemini-3.8-flash", validation_alias="GEMINI_MODEL"
    )
    claude_model: str = Field(
        default="claude-sonnet-4-6", validation_alias="CLAUDE_MODEL"
    )
    ollama_host: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_HOST"
    )
    ollama_model: str = Field(default="qwen3.5:9b", validation_alias="OLLAMA_MODEL")
    data_catalog_path: Path = Field(
        default=APP_ROOT / "data_catalogs",
        validation_alias="DATA_CATALOG_PATH",
    )
    data_path: Path = Field(
        default=REPOSITORY_ROOT / "datasets" / "factory",
        validation_alias="DATA_PATH",
    )
    output_path: Path = Field(
        default=APP_ROOT / "outputs", validation_alias="OUTPUT_PATH"
    )
    skills_path: Path = Field(
        default=APP_ROOT / "skills", validation_alias="SKILLS_PATH"
    )
    wiki_path: Path = Field(
        default=APP_ROOT / "wiki", validation_alias="WIKI_PATH"
    )
    log_path: Path = Field(
        default=APP_ROOT / "logs", validation_alias="LOG_PATH"
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    def validate_backend_keys(self) -> None:
        if self.backend == BackendType.CODEX and not self.openai_api_key:
            raise ConfigurationError(
                "BACKEND=CODEX requires OPENAI_API_KEY to be set."
            )
        if self.backend == BackendType.CODEX_CLI and self.codex_cli_timeout_seconds <= 0:
            raise ConfigurationError(
                "CODEX_CLI_TIMEOUT_SECONDS must be a positive integer."
            )
        if self.backend == BackendType.GEMINI and not self.gemini_api_key:
            raise ConfigurationError(
                "BACKEND=GEMINI requires GEMINI_API_KEY to be set."
            )
        if self.backend == BackendType.CLAUDE and not self.anthropic_api_key:
            raise ConfigurationError(
                "BACKEND=CLAUDE requires ANTHROPIC_API_KEY to be set."
            )
        if self.backend == BackendType.OLLAMA and not self.ollama_model.strip():
            raise ConfigurationError("BACKEND=OLLAMA requires OLLAMA_MODEL to be set.")


class ConfigurationError(Exception):
    pass


settings = Settings()
