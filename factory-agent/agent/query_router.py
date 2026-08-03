from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.context_builder import ContextBuilder
from agent.intent_detector import Intent, IntentDetector
from agent.planner import ExecutionPlan, Planner, RequestType
from agent.session_manager import Session, SessionManager
from agent.skill_selector import SkillSelector
from config.logging_config import get_logger
from data_access.loader import DataLoader
from guardrails.input_guard import InputGuard
from models.base import LLMBackend

logger = get_logger("query_router")


@dataclass
class RouteResult:
    skill_name: str | None
    skill_info: dict[str, Any] | None
    intent: Intent | None
    plan: ExecutionPlan | None = None
    error: str | None = None


class QueryRouter:
    def __init__(
        self,
        intent_detector: IntentDetector,
        skill_selector: SkillSelector,
        context_builder: ContextBuilder,
        data_loader: DataLoader,
        llm: LLMBackend | None = None,
    ) -> None:
        self._intent_detector = intent_detector
        self._skill_selector = skill_selector
        self._context_builder = context_builder
        self._data_loader = data_loader
        self._llm = llm
        self._planner = Planner()

    def route(self, query: str) -> RouteResult:
        try:
            query = InputGuard.validate_query(query)
        except Exception as e:
            return RouteResult(
                skill_name=None, skill_info=None, intent=None, error=str(e)
            )

        intent = self._intent_detector.detect(query)

        skill_info = (
            self._skill_selector.select(intent)
            if intent.skill_name not in ("help", "unknown")
            else None
        )
        plan = self._planner.create_plan(
            query=query,
            intent=intent,
            skill_info=skill_info,
            all_datasets=self._skill_selector.all_datasets(),
            all_catalogs=self._skill_selector.all_catalogs(),
        )

        planned_skill_info = {
            "required_datasets": plan.required_datasets,
            "required_catalogs": plan.required_catalogs,
        }
        if plan.request_type == RequestType.ACTION:
            planned_skill_name = plan.steps[0].skill_name
            planned_skill_info = skill_info or planned_skill_info
        elif intent.skill_name == "help":
            planned_skill_name = "help"
        else:
            planned_skill_name = plan.request_type.value.lower()

        return RouteResult(
            skill_name=planned_skill_name,
            skill_info=planned_skill_info,
            intent=intent,
            plan=plan,
        )
