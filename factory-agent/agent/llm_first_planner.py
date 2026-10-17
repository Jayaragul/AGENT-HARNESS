from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent.tool_registry import ToolDefinition
from models.base import LLMBackend


class LLMDecision(str, Enum):
    TOOL_CALLS = "tool_calls"
    ANSWER_FROM_CONTEXT = "answer_from_context"
    CLARIFICATION_REQUIRED = "clarification_required"
    SECURITY_REJECTED = "security_rejected"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class PlannedToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMToolPlan:
    decision: LLMDecision
    tool_calls: list[PlannedToolCall] = field(default_factory=list)
    message: str | None = None
    raw_response: str | None = None


class LLMFirstPlanner:
    MAX_TOOL_CALLS = 5
    ORDER_ID_PATTERN = re.compile(r"\b(ORD[-_]?\d+)\b", re.IGNORECASE)
    MATERIAL_ID_PATTERN = re.compile(r"\b([A-Z]{3}[-_]\d{3})\b", re.IGNORECASE)

    WRITE_PATTERNS: list[str] = [
        r"\b(delete|remove|drop|truncate|overwrite|update|edit|modify)\b",
        r"\b(write|save)\b.*\b(data|dataset|inventory|order|record)\b",
    ]

    def __init__(self, llm: LLMBackend | None = None) -> None:
        self._llm = llm

    def create_plan(
        self,
        query: str,
        catalog_context: str,
        tools: list[ToolDefinition],
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> LLMToolPlan:
        if self._matches_any(query, self.WRITE_PATTERNS):
            return LLMToolPlan(
                decision=LLMDecision.SECURITY_REJECTED,
                message=(
                    "I can't modify factory data directly, but I can help "
                    "you figure out what changes are needed."
                ),
            )

        if self._llm is None:
            return self._heuristic_plan(query, conversation_history)

        response = self._llm.generate(
            system_prompt=self._system_prompt(tools),
            user_prompt=self._user_prompt(query, conversation_history),
            context=catalog_context,
        )
        parsed = self._parse_json(response.content)
        if parsed is None:
            fallback = self._heuristic_plan(query, conversation_history)
            return LLMToolPlan(
                decision=fallback.decision,
                tool_calls=fallback.tool_calls,
                message=fallback.message,
                raw_response=response.content,
            )
        return self._plan_from_json(parsed, tools, response.content)

    def _system_prompt(self, tools: list[ToolDefinition]) -> str:
        tool_lines = []
        for tool in tools:
            tool_lines.append(
                json.dumps(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                )
            )

        return (
            "You are the planning layer for a read-only factory assistant. "
            "You decide whether the user request should be answered from approved "
            "catalog context, handled by approved tools, clarified, rejected for "
            "security, or marked unsupported. Python tools provide facts and "
            "calculations; do not calculate factory numbers yourself. Never invent "
            "tool names. Never request writes or unrestricted file access.\n\n"
            "Return only valid JSON in this exact shape:\n"
            "{"
            "\"decision\":\"tool_calls|answer_from_context|clarification_required|security_rejected|unsupported\","
            "\"message\":\"short user-facing note or clarification question\","
            "\"tool_calls\":[{\"name\":\"approved_tool_name\",\"arguments\":{}}]"
            "}\n\n"
            f"Approved tools:\n{chr(10).join(tool_lines)}"
        )

    def _user_prompt(
        self,
        query: str,
        conversation_history: list[dict[str, Any]] | None,
    ) -> str:
        recent = conversation_history[-4:] if conversation_history else []
        return (
            f"User question: {query}\n\n"
            f"Recent conversation entries:\n{json.dumps(recent, default=str)}"
        )

    def _plan_from_json(
        self,
        data: dict[str, Any],
        tools: list[ToolDefinition],
        raw_response: str,
    ) -> LLMToolPlan:
        approved = {tool.name for tool in tools}
        try:
            decision = LLMDecision(
                data.get("decision", LLMDecision.UNSUPPORTED.value)
            )
        except (TypeError, ValueError):
            return LLMToolPlan(
                decision=LLMDecision.UNSUPPORTED,
                message="The planning model returned an invalid decision.",
                raw_response=raw_response,
            )
        calls: list[PlannedToolCall] = []
        for item in data.get("tool_calls", [])[: self.MAX_TOOL_CALLS]:
            name = item.get("name")
            if name not in approved:
                continue
            arguments = item.get("arguments") or {}
            if isinstance(arguments, dict):
                calls.append(PlannedToolCall(name=name, arguments=arguments))

        if decision == LLMDecision.TOOL_CALLS and not calls:
            return LLMToolPlan(
                decision=LLMDecision.CLARIFICATION_REQUIRED,
                message=(
                    data.get("message")
                    or "I need a little more detail before choosing a tool."
                ),
                raw_response=raw_response,
            )

        return LLMToolPlan(
            decision=decision,
            tool_calls=calls,
            message=data.get("message"),
            raw_response=raw_response,
        )

    def _heuristic_plan(
        self,
        query: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> LLMToolPlan:
        query_lower = query.lower()
        order_id = self._extract_order_id(query)
        if order_id is None and self._looks_like_follow_up(query):
            order_id = self._last_order_id(conversation_history)
        material_id = self._extract_material_id(query)

        if any(word in query_lower for word in ("access", "acess", "data", "dataset", "catalog", "wiki")):
            return LLMToolPlan(
                decision=LLMDecision.ANSWER_FROM_CONTEXT,
                message=None,
            )

        if "risk" in query_lower or "report" in query_lower or "shortage" in query_lower:
            if order_id and "risk" not in query_lower:
                return LLMToolPlan(
                    decision=LLMDecision.TOOL_CALLS,
                    tool_calls=[
                        PlannedToolCall(
                            name="check_material_sufficiency",
                            arguments={"order_id": order_id},
                        )
                    ],
                )
            return LLMToolPlan(
                decision=LLMDecision.TOOL_CALLS,
                tool_calls=[PlannedToolCall(name="generate_material_risk_report")],
            )

        if material_id and any(word in query_lower for word in ("inventory", "stock", "material")):
            return LLMToolPlan(
                decision=LLMDecision.TOOL_CALLS,
                tool_calls=[
                    PlannedToolCall(
                        name="get_inventory_item",
                        arguments={"material_id": material_id},
                    )
                ],
            )

        if order_id and any(
            word in query_lower
            for word in ("complete", "manufacture", "produce", "fulfill", "feasible", "feasibility")
        ):
            return LLMToolPlan(
                decision=LLMDecision.TOOL_CALLS,
                tool_calls=[
                    PlannedToolCall(
                        name="get_order",
                        arguments={"order_id": order_id},
                    ),
                    PlannedToolCall(
                        name="check_material_sufficiency",
                        arguments={"order_id": order_id},
                    ),
                    PlannedToolCall(
                        name="get_machine_requirements",
                        arguments={"order_id": order_id},
                    ),
                ],
            )

        if order_id and any(word in query_lower for word in ("machine", "equipment", "hours", "time")):
            return LLMToolPlan(
                decision=LLMDecision.TOOL_CALLS,
                tool_calls=[
                    PlannedToolCall(
                        name="get_machine_requirements",
                        arguments={"order_id": order_id},
                    )
                ],
            )

        if order_id and any(
            word in query_lower
            for word in ("material", "inventory", "stock", "enough", "sufficient", "availability")
        ):
            return LLMToolPlan(
                decision=LLMDecision.TOOL_CALLS,
                tool_calls=[
                    PlannedToolCall(
                        name="check_material_sufficiency",
                        arguments={"order_id": order_id},
                    )
                ],
            )

        if order_id:
            return LLMToolPlan(
                decision=LLMDecision.CLARIFICATION_REQUIRED,
                message=(
                    "What would you like to check — materials, machines, or both?"
                ),
            )

        if any(word in query_lower for word in ("material", "machine", "order", "inventory")):
            return LLMToolPlan(
                decision=LLMDecision.CLARIFICATION_REQUIRED,
                message="Which order ID or item ID should I look up?",
            )

        return LLMToolPlan(
            decision=LLMDecision.UNSUPPORTED,
            message=(
                "I can help with questions about orders, inventory, machines, "
                "and production planning."
            ),
        )

    def _parse_json(self, content: str) -> dict[str, Any] | None:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return parsed if isinstance(parsed, dict) else None

    def _extract_order_id(self, query: str) -> str | None:
        match = self.ORDER_ID_PATTERN.search(query)
        return match.group(1).replace("_", "-").upper() if match else None

    def _extract_material_id(self, query: str) -> str | None:
        match = self.MATERIAL_ID_PATTERN.search(query.upper())
        return match.group(1).replace("_", "-") if match else None

    def _looks_like_follow_up(self, query: str) -> bool:
        query_lower = query.lower()
        return any(
            marker in query_lower
            for marker in ("what about", "how about", "same order", "that order", "it?")
        )

    def _last_order_id(
        self, conversation_history: list[dict[str, Any]] | None
    ) -> str | None:
        if not conversation_history:
            return None
        for entry in reversed(conversation_history):
            match = self.ORDER_ID_PATTERN.search(json.dumps(entry, default=str))
            if match:
                return match.group(1).replace("_", "-").upper()
        return None

    def _matches_any(self, query: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in patterns)
