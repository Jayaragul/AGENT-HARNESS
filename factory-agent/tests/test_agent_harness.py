from agent.harness import AgentHarness
from config.settings import Settings, BackendType


def test_harness_initialization() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    assert harness is not None


def test_harness_material_sufficiency() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("Do we have enough fabric for order ORD-1001?")
    assert resp["result"]["mode"] == "llm_first"
    assert resp["result"]["tools_used"] == ["check_material_sufficiency"]
    tool_result = resp["result"]["tool_results"][0]["result"]
    assert tool_result["overall_status"] == "insufficient"
    assert tool_result["order_id"] == "ORD-1001"
    assert resp["wiki_pages_consulted"] is not None
    assert resp["data_revision"]["format"] == "factory-data-sha256-v1"
    assert resp["data_revision"]["id"].startswith("factory-data-sha256-v1:")


def test_harness_machine_requirements() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("What machines are needed for order ORD-1002?")
    assert resp["result"]["tools_used"] == ["get_machine_requirements"]
    tool_result = resp["result"]["tool_results"][0]["result"]
    assert tool_result["total_hours"] > 0


def test_harness_material_risk_report() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("Generate a material risk report")
    assert resp["result"]["tools_used"] == ["generate_material_risk_report"]
    tool_result = resp["result"]["tool_results"][0]["result"]
    assert tool_result["total_active_orders"] > 0


def test_harness_unknown_question_is_unsupported() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("What is the weather?")
    assert resp.get("error") is None
    assert resp["skill_name"] == "unsupported"
    assert resp["result"]["mode"] == "llm_first"


def test_harness_greeting_gets_friendly_capabilities_answer() -> None:
    harness = AgentHarness(Settings(backend=BackendType.MOCK))
    resp = harness.process_query("hey what can you do for me")

    assert resp["skill_name"] == "answer_from_context"
    assert "Hi!" in resp["explanation"]
    assert "material availability" in resp["explanation"]
    assert "available_tools:" not in resp["explanation"]


def test_harness_factory_overview_is_grounded_and_user_facing() -> None:
    harness = AgentHarness(Settings(backend=BackendType.MOCK))
    resp = harness.process_query("tell me about the factory")

    assert resp["skill_name"] == "answer_from_context"
    assert "orders, inventory, materials, machines" in resp["explanation"]
    assert "live factory-system connection" in resp["explanation"]
    assert "decision:" not in resp["explanation"]


def test_harness_help_query() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("What data do you have?")
    assert resp["skill_name"] == "answer_from_context"
    assert "orders.md" in resp["result"]["source_catalogs"]
    assert "list_available_datasets" in resp["result"]["available_tools"]


def test_harness_access_query_uses_help() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("what you have acess too")
    assert resp["skill_name"] == "answer_from_context"
    assert "orders.md" in resp["result"]["source_catalogs"]


def test_harness_missing_order_id() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("Check material sufficiency?")
    assert resp.get("error") is None
    assert resp["skill_name"] == "clarification_required"
    assert "order ID" in resp["result"]["message"]


def test_harness_rejects_write_requests() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("Delete inventory record FAB-001.")
    assert resp.get("error") is None
    assert resp["skill_name"] == "security_rejected"
    assert resp["warnings"]


def test_harness_feasibility_uses_multiple_tools() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("Can we complete order ORD-1001?")
    assert resp["result"]["tools_used"] == [
        "get_order",
        "check_material_sufficiency",
        "get_machine_requirements",
    ]
    assert resp["skill_name"] == "order_feasibility"


def test_harness_emits_correlated_trace() -> None:
    harness = AgentHarness(Settings(backend=BackendType.MOCK))
    resp = harness.process_query("What machines are needed for ORD-1002?")

    assert resp["trace"]["run_id"] == resp["audit_id"]
    assert resp["trace"]["metadata"]["data_revision"]["id"] == resp["data_revision"]["id"]
    stages = [event["stage"] for event in resp["trace"]["events"]]
    assert stages[:4] == [
        "input_guard",
        "context",
        "wiki_retrieval",
        "planning",
    ]
    assert "tool:0:get_machine_requirements" in stages
    assert stages[-1] == "synthesis"


def test_harness_resolves_follow_up_from_session() -> None:
    harness = AgentHarness(Settings(backend=BackendType.MOCK))
    first = harness.process_query("Do we have enough material for ORD-1002?")
    second = harness.process_query(
        "What about machines for that order?",
        session_id=first["session_id"],
    )

    assert second["result"]["tools_used"] == ["get_machine_requirements"]
    assert second["result"]["tool_results"][0]["result"]["order_id"] == "ORD-1002"


def test_wiki_lint() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("lint")
    assert resp["skill_name"] == "wiki_lint"
    assert "total_pages_count" in resp["result"]
    assert "issues" in resp["result"]


def test_wiki_index() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("wiki index")
    assert resp["skill_name"] == "wiki_index"
    assert "Wiki" in resp["result"]["message"]


def test_wiki_log() -> None:
    settings = Settings(backend=BackendType.MOCK)
    harness = AgentHarness(settings)
    resp = harness.process_query("wiki log")
    assert resp["skill_name"] == "wiki_log"
    assert "Wiki Activity" in resp["result"]["message"]
