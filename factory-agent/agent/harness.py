from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.context_builder import ContextBuilder
from agent.llm_first_planner import LLMDecision, LLMFirstPlanner
from agent.prompt_orchestrator import PromptOrchestrator
from agent.response_synthesizer import ResponseSynthesizer
from agent.session_manager import SessionManager
from agent.skill_registry import SkillRegistry
from agent.tool_registry import ToolExecutionError, ToolRegistry
from agent.trace import AgentTrace
from agent.run_context import RunContext
from agent.tool_executor import AuthorizedToolExecutor
from agent.wiki_manager import WikiManager
from config.logging_config import get_logger, setup_logging, shutdown_logging
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

        self._logger = setup_logging(self._settings.log_path, self._settings.log_level)

        self._data_loader = DataLoader(self._settings.data_path)
        self._llm: LLMBackend | None = None
        if self._settings.backend.value != "MOCK":
            self._llm = create_backend(self._settings)

        self._skill_registry = SkillRegistry(self._settings.skills_path)
        self._context_builder = ContextBuilder(self._settings.data_catalog_path)
        self._tool_registry = ToolRegistry(self._data_loader, self._context_builder)
        self._llm_first_planner = LLMFirstPlanner(self._llm)
        self._prompt_orchestrator = PromptOrchestrator(self._llm)
        self._writer = Writer(self._settings.output_path)
        self._response_synthesizer = ResponseSynthesizer(
            self._prompt_orchestrator, self._writer
        )
        self._session_manager = SessionManager()
        self._wiki = WikiManager(self._settings.wiki_path)

        self._logger.info(
            "AgentHarness initialized — three-layer wiki pattern",
            extra={
                "backend": self._settings.backend.value,
                "data_path": str(self._settings.data_path),
                "wiki_path": str(self._settings.wiki_path),
            },
        )

    # ── Public entry point ─────────────────────────────────────────

    def close(self) -> None:
        close_backend = getattr(self._llm, "close", None)
        if callable(close_backend):
            close_backend()
        shutdown_logging()

    def process_query(
        self,
        query: str,
        session_id: str | None = None,
        generate_report: bool = False,
    ) -> dict[str, Any]:
        audit_id = str(uuid4())[:8]
        trace = AgentTrace(audit_id)
        data_revision = self._data_loader.revision.as_dict()
        trace.set_metadata("data_revision", data_revision)
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
            response = self._handle_lint(session, audit_id)
            response["trace"] = trace.as_dict()
            response["data_revision"] = data_revision
            return response

        # ── Wiki query operation ────────────────────────────────
        if query_lower.startswith("wiki "):
            wiki_query = query[5:].strip()
            response = self._handle_wiki_query(wiki_query, session, audit_id)
            response["trace"] = trace.as_dict()
            response["data_revision"] = data_revision
            return response

        # ── Main flow: wiki-first query → tools → ingest ───────
        response = self._process_wiki_first(
            query=query,
            session=session,
            audit_id=audit_id,
            trace=trace,
            generate_report=generate_report,
        )
        response["data_revision"] = data_revision
        return response

    # ── Wiki-first query flow ───────────────────────────────────

    def _process_wiki_first(
        self,
        query: str,
        session: Any,
        audit_id: str,
        trace: AgentTrace,
        generate_report: bool = False,
    ) -> dict[str, Any]:
        """Check wiki first, then fall through to LLM planner + ingest."""
        trace.start("input_guard")
        try:
            query = InputGuard.validate_query(query)
        except Exception as e:
            trace.end("input_guard", status="rejected", details={"error": str(e)})
            response = self._error_response(session, audit_id, query, str(e))
            response["trace"] = trace.as_dict()
            return response
        trace.end("input_guard")

        wiki_pages_consulted: list[str] = []
        wiki_answer: str | None = None

        # Phase 1: Check wiki for relevant knowledge
        skill_info = {
            "required_datasets": self._skill_registry.all_datasets(),
            "required_catalogs": self._skill_registry.all_catalogs(),
        }
        trace.start("context")
        catalog_context = self._context_builder.build_context(
            skill_info=skill_info, intent=None,
        )
        trace.end(
            "context",
            details={
                "catalogs": skill_info["required_catalogs"],
                "context_chars": len(catalog_context),
            },
        )

        trace.start("wiki_retrieval")
        keyword = self._extract_search_keyword(query)
        if keyword:
            matches = self._wiki.search_pages(keyword)
            for m in matches[:3]:
                try:
                    page_content = self._wiki.read_page(m["category"], m["name"])
                    wiki_pages_consulted.append(f"{m['category']}/{m['name']}")
                except Exception:
                    continue
        trace.end(
            "wiki_retrieval",
            details={"keyword": keyword, "pages": wiki_pages_consulted},
        )

        # Phase 2: LLM planner decides what tools to call
        trace.start("planning")
        definitions = self._tool_registry.definitions()
        run_context = RunContext(
            task_id=audit_id,
            authorized_tools=frozenset(tool.name for tool in definitions),
        )
        tool_executor = AuthorizedToolExecutor(self._tool_registry, run_context)
        plan = self._llm_first_planner.create_plan(
            query=query,
            catalog_context=catalog_context,
            tools=definitions,
            conversation_history=session.history,
        )
        trace.end(
            "planning",
            details={
                "decision": plan.decision.value,
                "tool_calls": [call.name for call in plan.tool_calls],
            },
        )

        warnings: list[str] = []
        tool_results: list[dict[str, Any]] = []

        if plan.decision == LLMDecision.TOOL_CALLS:
            for index, call in enumerate(plan.tool_calls):
                stage = f"tool:{index}:{call.name}"
                trace.start(stage)
                try:
                    tool_result = tool_executor.execute(
                        call.name, call.arguments,
                    )
                    tool_results.append({
                        "tool": call.name,
                        "arguments": call.arguments,
                        "result": tool_result,
                    })
                    trace.end(stage, details={"arguments": call.arguments})
                except (ToolExecutionError, ValueError, TypeError) as e:
                    warnings.append(f"{call.name} failed: {str(e)}")
                    tool_results.append({
                        "tool": call.name,
                        "arguments": call.arguments,
                        "error": str(e),
                    })
                    trace.end(
                        stage,
                        status="error",
                        details={"arguments": call.arguments, "error": str(e)},
                    )
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
        detected_skills: list[str] = []
        for item in tool_results:
            tool_result_data = item.get("result", {})
            if not isinstance(tool_result_data, dict):
                continue
            detected_skill = tool_result_data.get("skill", "")
            if not detected_skill:
                continue
            self._wiki.ingest_result(
                skill_name=detected_skill,
                query=query,
                result=tool_result_data,
            )
            detected_skills.append(detected_skill)

        if len(plan.tool_calls) > 1:
            skill_name = "order_feasibility"
        elif detected_skills:
            skill_name = detected_skills[0]

        trace.start("synthesis")
        response = self._response_synthesizer.synthesize(
            result=result,
            query=query,
            skill_name=skill_name,
            datasets=skill_info["required_datasets"],
            warnings=warnings if warnings else None,
            session_id=session.session_id,
            context=catalog_context,
            wiki_pages_consulted=wiki_pages_consulted,
            audit_id=audit_id,
        )
        # Keep short conversational answers user-facing. Do not feed planner
        # diagnostics (tool names, decisions, catalog lists) into the chat UI.
        if plan.message and plan.decision in {
            LLMDecision.ANSWER_FROM_CONTEXT,
            LLMDecision.UNSUPPORTED,
            LLMDecision.CLARIFICATION_REQUIRED,
            LLMDecision.SECURITY_REJECTED,
        }:
            response["explanation"] = plan.message
        trace.end("synthesis")
        response["trace"] = trace.as_dict()

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
