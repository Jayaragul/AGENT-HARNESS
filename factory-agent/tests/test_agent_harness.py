from pathlib import Path

import pytest

from agent.harness import AgentHarness
from agent.intent_detector import IntentDetector
from agent.skill_selector import SkillSelector
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


def test_intent_detector() -> None:
    detector = IntentDetector()
    intent = detector.detect("Do we have enough fabric for ORD-1001?")
    assert intent.skill_name == "material_sufficiency"
    assert intent.entities["order_id"] == "ORD-1001"


def test_intent_detector_unknown() -> None:
    detector = IntentDetector()
    intent = detector.detect("What is the meaning of life?")
    assert intent.skill_name == "unknown"


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
