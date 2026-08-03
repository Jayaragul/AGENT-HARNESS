from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.context_builder import ContextBuilder
from agent.intent_detector import IntentDetector
from agent.llm_first_planner import LLMDecision, LLMFirstPlanner
from agent.planner import RequestType
from agent.prompt_orchestrator import PromptOrchestrator
from agent.query_router import QueryRouter
from agent.response_synthesizer import ResponseSynthesizer
from agent.session_manager import SessionManager
from agent.skill_selector import SkillSelector
from agent.tool_registry import ToolExecutionError, ToolRegistry
from agent.wiki_manager import WikiManager
from config.logging_config import get_logger, setup_logging
from config.settings import Settings
from data_access.loader import DataLoader
from guardrails.input_guard import InputGuard
from models.base import LLMBackend
from models.factory import create_backend
from output_service.writer import Writer

logger = get_logger("harness")


class AgentHarness:
    """Three-layer AI Agent Harness (Karpathy LLM-Wiki pattern).

    Layers:
      - Raw sources: immutable CSV data in data/
      - The Wiki:    persistent markdown knowledge base in wiki/
      - Schema:      skill.md, data_catalogs/, tool definitions

    Operations:
      - Query:  check wiki first → run tools if stale → respond
      - Ingest: file skill results into wiki for compounding knowledge
      - Lint:   health-check the wiki for orphans, gaps, staleness
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._settings.validate_backend_keys()

        self._logger = setup_logging(Path("logs"), self._settings.log_level)

        self._data_loader = DataLoader(self._settings.data_path)
        self._llm: LLMBackend | None = None
        if self._settings.backend.value != "MOCK":
            self._llm = create_backend(self._settings)

        self._intent_detector = IntentDetector()
        self._skill_selector = SkillSelector(Path("skills"))
        self._context_builder = ContextBuilder(self._settings.data_catalog_path)
        self._tool_registry = ToolRegistry(self._data_loader, self._context_builder)
        self._llm_first_planner = LLMFirstPlanner(self._llm)
        self._prompt_orchestrator = PromptOrchestrator(self._llm)
        self._writer = Writer(self._settings.output_path)
        self._response_synthesizer = ResponseSynthesizer(
            self._prompt_orchestrator, self._writer
        )
        self._session_manager = SessionManager()
        self._wiki = WikiManager(Path("wiki"))

        self._query_router = QueryRouter(
            intent_detector=self._intent_detector,
            skill_selector=self._skill_selector,
            context_builder=self._context_builder,
            data_loader=self._data_loader,
            llm=self._llm,
        )

        self._logger.info(
            "AgentHarness initialized — three-layer wiki pattern",
            extra={
                "backend": self._settings.backend.value,
                "data_path": str(self._settings.data_path),
                "wiki_path": "wiki/",
            },
        )

    # ── Public entry point ─────────────────────────────────────────

    def process_query(
        self,
        query: str,
        session_id: str | None = None,
        generate_report: bool = False,
    ) -> dict[str, Any]:
        audit_id = str(uuid4())[:8]
        session = self._session_manager.get_or_create(session_id)

        logger.info(
            "Processing query",
            extra={
                "audit_id": audit_id,
                "session_id": session.session_id,
                "query": query[:100],
            },
        )

        session.add_entry({"query": query, "audit_id": audit_id})

        query_lower = query.strip().lower()

        # ── Lint operation ──────────────────────────────────────
        if query_lower in ("lint", "wiki lint", "health check", "wiki health"):
            return self._handle_lint(session, audit_id)

        # ── Wiki query operation ────────────────────────────────
        if query_lower.startswith("wiki "):
            wiki_query = query[5:].strip()
            return self._handle_wiki_query(wiki_query, session, audit_id)

        # ── Main flow: wiki-first query → tools → ingest ───────
        return self._process_wiki_first(
            query=query,
            session=session,
            audit_id=audit_id,
            generate_report=generate_report,
        )

    # ── Wiki-first query flow ───────────────────────────────────

    def _process_wiki_first(
        self,
        query: str,
        session: Any,
        audit_id: str,
        generate_report: bool = False,
    ) -> dict[str, Any]:
        """Check wiki first, then fall through to LLM planner + ingest."""
        try:
            query = InputGuard.validate_query(query)
        except Exception as e:
            return self._error_response(session, audit_id, query, str(e))

        wiki_pages_consulted: list[str] = []
        wiki_answer: str | None = None

        # Phase 1: Check wiki for relevant knowledge
        skill_info = {
            "required_datasets": self._skill_selector.all_datasets(),
            "required_catalogs": self._skill_selector.all_catalogs(),
        }
        catalog_context = self._context_builder.build_context(
            skill_info=skill_info, intent=None,
        )

        keyword = self._extract_search_keyword(query)
        if keyword:
            matches = self._wiki.search_pages(keyword)
            for m in matches[:3]:
                try:
                    page_content = self._wiki.read_page(m["category"], m["name"])
                    wiki_pages_consulted.append(f"{m['category']}/{m['name']}")
                except Exception:
                    continue

        # Phase 2: LLM planner decides what tools to call
        plan = self._llm_first_planner.create_plan(
            query=query,
            catalog_context=catalog_context,
            tools=self._tool_registry.definitions(),
            conversation_history=session.history,
        )

        warnings: list[str] = []
        tool_results: list[dict[str, Any]] = []

        if plan.decision == LLMDecision.TOOL_CALLS:
            for call in plan.tool_calls:
                try:
                    tool_result = self._tool_registry.execute(
                        call.name, call.arguments,
                    )
                    tool_results.append({
                        "tool": call.name,
                        "arguments": call.arguments,
                        "result": tool_result,
                    })
                except (ToolExecutionError, ValueError, TypeError) as e:
                    warnings.append(f"{call.name} failed: {str(e)}")
                    tool_results.append({
                        "tool": call.name,
                        "arguments": call.arguments,
                        "error": str(e),
                    })
        elif plan.decision == LLMDecision.SECURITY_REJECTED:
            warnings.append("Request blocked by read-only data access policy.")

        result = {
            "mode": "llm_first",
            "decision": plan.decision.value,
            "message": plan.message,
            "available_tools": self._tool_registry.list_tool_names(),
            "tools_used": [item["tool"] for item in tool_results],
            "tool_results": tool_results,
            "source_catalogs": skill_info["required_catalogs"],
        }

        # Phase 3: Ingest into wiki so knowledge compounds
        skill_name = plan.decision.value
        if tool_results and tool_results[0].get("result"):
            tool_result_data = tool_results[0].get("result", {})
            if isinstance(tool_result_data, dict):
                detected_skill = tool_result_data.get("skill", "")
                if detected_skill:
                    self._wiki.ingest_result(
                        skill_name=detected_skill,
                        query=query,
                        result=tool_result_data,
                    )
                    skill_name = detected_skill

        response = self._response_synthesizer.synthesize(
            result=result,
            query=query,
            skill_name=skill_name,
            datasets=skill_info["required_datasets"],
            warnings=warnings if warnings else None,
            session_id=session.session_id,
            context=catalog_context,
            wiki_pages_consulted=wiki_pages_consulted,
        )

        session.add_entry(response)

        if generate_report:
            report_path = self._response_synthesizer.write_report(response)
            response["report_path"] = report_path

        return response

    # ── Lint operation ──────────────────────────────────────────

    def _handle_lint(self, session: Any, audit_id: str) -> dict[str, Any]:
        lint_result = self._wiki.lint()
        response = {
            "session_id": session.session_id,
            "audit_id": audit_id,
            "query": "lint",
            "skill_name": "wiki_lint",
            "datasets_used": [],
            "result": lint_result,
            "explanation": self._format_lint_explanation(lint_result),
            "warnings": [],
        }
        session.add_entry(response)
        return response

    def _format_lint_explanation(self, lint_result: dict[str, Any]) -> str:
        lines = ["## Wiki Health Check\n"]
        lines.append(f"Total pages: {lint_result['total_pages_count']}")
        if lint_result["issues"]:
            lines.append(f"Issues found: {lint_result['issues_count']}")
            for issue in lint_result["issues"]:
                lines.append(f"  - {issue}")
        else:
            lines.append("No issues found — wiki is healthy.")
        return "\n".join(lines)

    # ── Wiki query operation ────────────────────────────────────

    def _handle_wiki_query(
        self, wiki_query: str, session: Any, audit_id: str,
    ) -> dict[str, Any]:
        parts = wiki_query.split(" ", 1)
        action = parts[0].lower()

        if action == "index":
            content = self._wiki.read_index()
            return self._wiki_text_response(session, audit_id, content, "wiki_index")
        elif action == "log":
            lines = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
            content = self._wiki.read_log(lines=lines)
            return self._wiki_text_response(session, audit_id, content, "wiki_log")
        elif action == "search" and len(parts) > 1:
            results = self._wiki.search_pages(parts[1])
            if not results:
                return self._wiki_text_response(
                    session, audit_id, "No pages found.", "wiki_search"
                )
            content = "\n\n".join(
                f"**{r['name']}** ({r['category']}): {r['snippet']}..."
                for r in results
            )
            return self._wiki_text_response(session, audit_id, content, "wiki_search")
        elif action == "list":
            category = parts[1] if len(parts) > 1 else None
            pages = self._wiki.list_pages(category)
            if not pages:
                return self._wiki_text_response(
                    session, audit_id, "No pages found.", "wiki_list"
                )
            content = "\n".join(
                f"- {p['name']} ({p['category']})" for p in pages
            )
            return self._wiki_text_response(session, audit_id, content, "wiki_list")
        else:
            return self._wiki_text_response(
                session, audit_id,
                "Wiki commands: index, log [N], search <term>, list [category]",
                "wiki_help",
            )

    def _wiki_text_response(
        self, session: Any, audit_id: str, text: str, skill_name: str,
    ) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "audit_id": audit_id,
            "query": text[:60],
            "skill_name": skill_name,
            "datasets_used": [],
            "result": {"message": text},
            "explanation": text,
            "warnings": [],
        }

    # ── Helpers ─────────────────────────────────────────────────

    def _extract_search_keyword(self, query: str) -> str | None:
        import re
        patterns = [
            r"(?:order|ORD)[-\s]?(\d+)",
            r"(?:material|item)[-\s]?(\w{3,4}[-\s]?\d+)",
            r"(?:fabric|wood|steel|paint|screw|hinge|handle)[a-z]*",
        ]
        for p in patterns:
            m = re.search(p, query, re.IGNORECASE)
            if m:
                return m.group(0)
        words = query.lower().split()
        for w in words:
            if len(w) > 4:
                return w
        return None

    def _error_response(
        self, session: Any, audit_id: str, query: str, error: str,
    ) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "audit_id": audit_id,
            "query": query,
            "error": error,
            "skill_name": "input_rejected",
            "datasets_used": [],
            "result": None,
            "explanation": error,
            "warnings": [],
        }
