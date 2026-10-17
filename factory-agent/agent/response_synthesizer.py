from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from agent.prompt_orchestrator import PromptOrchestrator
from config.logging_config import get_logger
from output_service.writer import Writer

logger = get_logger("response_synthesizer")


class ResponseSynthesizer:
    def __init__(
        self,
        prompt_orchestrator: PromptOrchestrator | None = None,
        writer: Writer | None = None,
    ) -> None:
        self._orchestrator = prompt_orchestrator
        self._writer = writer

    def synthesize(
        self,
        result: dict[str, Any],
        query: str,
        skill_name: str,
        datasets: list[str],
        warnings: list[str] | None = None,
        session_id: str | None = None,
        context: str | None = None,
        wiki_pages_consulted: list[str] | None = None,
        audit_id: str | None = None,
    ) -> dict[str, Any]:
        warnings = warnings or []
        audit_id = audit_id or str(uuid4())[:8]

        explanation = None
        if self._orchestrator:
            explanation = self._orchestrator.generate_explanation(
                result,
                query,
                skill_name=skill_name,
                context=context,
            )
            if not explanation:
                explanation = self._format_basic_response(result)

        response: dict[str, Any] = {
            "session_id": session_id,
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "skill_name": skill_name,
            "datasets_used": datasets,
            "result": result,
            "explanation": explanation,
            "warnings": warnings,
            "wiki_pages_consulted": wiki_pages_consulted or [],
        }

        logger.info(
            "Response synthesized",
            extra={
                "audit_id": audit_id,
                "skill": skill_name,
                "datasets": datasets,
            },
        )

        return response

    def _format_basic_response(self, result: dict[str, Any]) -> str:
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

    def write_report(
        self,
        response: dict[str, Any],
        writer: Writer | None = None,
    ) -> str | None:
        w = writer or self._writer
        if w is None:
            return None
        path = w.write_report(
            data=response.get("result", {}),
            report_name=response.get("skill_name", "report").replace(" ", "_"),
            skill_name=response.get("skill_name", ""),
            source_datasets=response.get("datasets_used", []),
            query=response.get("query", ""),
            result_summary=str(response.get("explanation", ""))[:200],
            warnings=response.get("warnings", []),
            fmt="json",
        )
        return str(path)
