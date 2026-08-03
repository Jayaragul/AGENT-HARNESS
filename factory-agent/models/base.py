from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    content: str
    model_name: str
    usage: dict[str, int] | None = None
    raw: Any | None = None


@dataclass
class ModelConfig:
    temperature: float = 0.0
    max_tokens: int = 2048
    top_p: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


class LLMBackend(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        ...
