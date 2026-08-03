from __future__ import annotations

from typing import Any

from models.base import LLMBackend


class PromptOrchestrator:
    def __init__(self, llm: LLMBackend | None = None) -> None:
        self._llm = llm

    def generate_explanation(
        self,
        result: dict[str, Any],
        query: str,
        skill_name: str | None = None,
        context: str | None = None,
    ) -> str:
        if self._llm is None:
            return self._format_result_as_text(result)

        if skill_name in ("unsupported", "clarification_required", "security_rejected"):
            system_prompt = (
                "You are a factory AI assistant. Answer briefly and naturally. "
                "If you cannot do something, say what you can do instead. "
                "Never mention tools, capabilities, or internal systems."
            )
        else:
            system_prompt = (
                "You are a factory AI assistant. Answer directly and concisely "
                "using only the facts provided. No greetings, no introductions, "
                "no explanations of what you can do. Just the answer."
            )

        user_prompt = (
            f"Query: {query}\n\n"
            f"Data:\n{self._format_result_as_text(result)}"
        )

        response = self._llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context,
        )
        return response.content

    def _format_result_as_text(self, result: dict[str, Any]) -> str:
        lines: list[str] = []
        for key, value in result.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
