from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class BackendType(str, Enum):
    CODEX = "CODEX"
    GEMINI = "GEMINI"
    MOCK = "MOCK"


class Settings(BaseSettings):
    backend: BackendType = BackendType.CODEX
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    data_catalog_path: Path = Field(
        default=Path("data_catalogs"),
        validation_alias="DATA_CATALOG_PATH",
    )
    data_path: Path = Field(default=Path("../datasets/factory"), validation_alias="DATA_PATH")
    output_path: Path = Field(default=Path("outputs"), validation_alias="OUTPUT_PATH")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_backend_keys(self) -> None:
        if self.backend == BackendType.CODEX and not self.openai_api_key:
            raise ConfigurationError(
                "BACKEND=CODEX requires OPENAI_API_KEY to be set."
            )
        if self.backend == BackendType.GEMINI and not self.gemini_api_key:
            raise ConfigurationError(
                "BACKEND=GEMINI requires GEMINI_API_KEY to be set."
            )


class ConfigurationError(Exception):
    pass


settings = Settings()
