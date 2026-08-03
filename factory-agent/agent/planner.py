from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent.intent_detector import Intent


class RequestType(str, Enum):
    ACTION = "ACTION"
    KNOWLEDGE = "KNOWLEDGE"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    SECURITY_REJECTED = "SECURITY_REJECTED"


@dataclass(frozen=True)
class PlanStep:
    skill_name: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    request_type: RequestType
    steps: list[PlanStep] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    required_datasets: list[str] = field(default_factory=list)
    required_catalogs: list[str] = field(default_factory=list)
    message: str | None = None


class Planner:
    WRITE_PATTERNS: list[str] = [
        r"\b(delete|remove|drop|truncate|overwrite|update|edit|modify)\b",
        r"\b(write|save)\b.*\b(data|dataset|inventory|order|record)\b",
    ]

    KNOWLEDGE_PATTERNS: list[str] = [
        r"\bwhat\b.*\b(data|dataset|field|column|catalog|wiki|access|acess)\b",
        r"\bexplain\b.*\b(data|dataset|field|column|catalog|wiki)\b",
        r"\bwhat\b.*\b(lead time|supplier|unit cost|min stock|machine status)\b",
        r"\blist\b.*\b(data|dataset|field|column|catalog|wiki)\b",
    ]

    AMBIGUOUS_ORDER_PATTERNS: list[str] = [
        r"\b(check|review|analyze|analyse|look at|show)\b.*\bORD[-_]?\d+\b",
    ]

    def create_plan(
        self,
        query: str,
        intent: Intent,
        skill_info: dict[str, Any] | None,
        all_datasets: list[str],
        all_catalogs: list[str],
    ) -> ExecutionPlan:
        query_lower = query.lower()

        if self._matches_any(query_lower, self.WRITE_PATTERNS):
            return ExecutionPlan(
                request_type=RequestType.SECURITY_REJECTED,
                required_datasets=all_datasets,
                required_catalogs=all_catalogs,
                message=(
                    "I only have read-only access to the factory data, so I cannot "
                    "delete, edit, or overwrite records."
                ),
            )

        if intent.skill_name == "help" or self._matches_any(
            query_lower, self.KNOWLEDGE_PATTERNS
        ):
            return ExecutionPlan(
                request_type=RequestType.KNOWLEDGE,
                required_datasets=all_datasets,
                required_catalogs=all_catalogs,
                message="Answer from the approved data catalog/wiki context.",
            )

        if intent.skill_name != "unknown" and skill_info is not None:
            missing = self._missing_required_parameters(intent, skill_info)
            if missing:
                return ExecutionPlan(
                    request_type=RequestType.CLARIFICATION_REQUIRED,
                    required_datasets=skill_info.get("required_datasets", []),
                    required_catalogs=skill_info.get("required_catalogs", []),
                    message=self._clarification_message(intent.skill_name, missing),
                )

            return ExecutionPlan(
                request_type=RequestType.ACTION,
                steps=[
                    PlanStep(
                        skill_name=intent.skill_name,
                        parameters=dict(intent.entities),
                    )
                ],
                parameters=dict(intent.entities),
                required_datasets=skill_info.get("required_datasets", []),
                required_catalogs=skill_info.get("required_catalogs", []),
            )

        if self._matches_any(query_lower, self.AMBIGUOUS_ORDER_PATTERNS):
            return ExecutionPlan(
                request_type=RequestType.CLARIFICATION_REQUIRED,
                parameters=dict(intent.entities),
                required_datasets=all_datasets,
                required_catalogs=all_catalogs,
                message=(
                    "Which check do you want for this order: material sufficiency, "
                    "machine requirements, or material risk?"
                ),
            )

        return ExecutionPlan(
            request_type=RequestType.UNSUPPORTED,
            required_datasets=all_datasets,
            required_catalogs=all_catalogs,
            message=(
                "I could not match that to an approved factory skill or data wiki "
                "question. I can help with material sufficiency, machine "
                "requirements, material risk reports, and questions about the "
                "available data catalogs."
            ),
        )

    def _missing_required_parameters(
        self,
        intent: Intent,
        skill_info: dict[str, Any],
    ) -> list[str]:
        missing: list[str] = []
        for name, spec in skill_info.get("required_parameters", {}).items():
            if spec.get("required", True) and not intent.entities.get(name):
                missing.append(name)
        return missing

    def _clarification_message(self, skill_name: str, missing: list[str]) -> str:
        if missing == ["order_id"]:
            return (
                f"I can run {skill_name}, but I need an order ID first "
                "(for example, ORD-1001)."
            )
        return f"I need these parameters before running {skill_name}: {', '.join(missing)}."

    def _matches_any(self, query: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in patterns)
