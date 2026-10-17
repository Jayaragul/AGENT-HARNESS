import pytest

from agent.run_context import RunContext
from agent.tool_executor import AuthorizedToolExecutor
from agent.tool_registry import ToolExecutionError


class FakeRegistry:
    def __init__(self):
        self.invocations = []

    def list_tool_names(self):
        return ["read_record"]

    def execute(self, name, arguments):
        self.invocations.append((name, arguments))
        return {"ok": True}


def test_authorized_tool_call_reaches_registry():
    registry = FakeRegistry()
    executor = AuthorizedToolExecutor(
        registry, RunContext(task_id="run-1", authorized_tools=frozenset({"read_record"}))
    )
    assert executor.execute("read_record", {"record_id": "r1"}) == {"ok": True}
    assert len(registry.invocations) == 1


@pytest.mark.parametrize(
    "name,args,enabled,code",
    [
        ("read_record", {}, frozenset(), "TOOL_DISABLED"),
        ("unregistered", {}, frozenset({"unregistered"}), "TOOL_DISABLED"),
        ("read_record", {"tenant_id": "attacker"}, frozenset({"read_record"}), "SCOPE_DENIED"),
    ],
)
def test_denied_call_never_invokes_registry(name, args, enabled, code):
    registry = FakeRegistry()
    executor = AuthorizedToolExecutor(
        registry, RunContext(task_id="run-1", authorized_tools=enabled)
    )
    with pytest.raises(ToolExecutionError, match=code):
        executor.execute(name, args)
    assert registry.invocations == []
