from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.run_context import RunContext
from agent.tool_registry import ToolExecutionError, ToolRegistry


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    value: dict[str, Any] | None = None
    error_code: str | None = None
    error: str | None = None


class AuthorizedToolExecutor:
    """Single policy boundary for all planner/model-originated tool calls."""

    IDENTITY_FIELDS = frozenset({"actor_id", "user_id", "tenant_id", "scope"})

    def __init__(self, registry: ToolRegistry, context: RunContext) -> None:
        self._registry = registry
        self._context = context

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if name not in self._context.authorized_tools:
            raise ToolExecutionError(f"TOOL_DISABLED: Tool '{name}' is not enabled for this run.")
        arguments = arguments or {}
        if not isinstance(arguments, dict):
            raise ToolExecutionError("INVALID_ARGUMENTS: Tool arguments must be an object.")
        if self.IDENTITY_FIELDS.intersection(arguments):
            raise ToolExecutionError("SCOPE_DENIED: Caller identity and scope are server-controlled.")
        if name not in self._registry.list_tool_names():
            raise ToolExecutionError(f"TOOL_DISABLED: Tool '{name}' is not registered.")
        try:
            return self._registry.execute(name, arguments)
        except ToolExecutionError as exc:
            raise ToolExecutionError(f"INVALID_ARGUMENTS: {exc}") from exc
