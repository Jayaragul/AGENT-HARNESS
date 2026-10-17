"""End-to-end evaluation tests for the separated factory project."""

import importlib
import json
from pathlib import Path

import pytest

from agent.harness import AgentHarness
from config.settings import BackendType, Settings
from data_access.loader import DataLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTORY_DATA = PROJECT_ROOT / "datasets" / "factory"


@pytest.fixture
def mock_harness() -> AgentHarness:
    return AgentHarness(Settings(backend=BackendType.MOCK))


def test_active_factory_dataset_is_separate_and_complete() -> None:
    settings = Settings(backend=BackendType.MOCK)
    assert settings.data_path.resolve() == FACTORY_DATA.resolve()
    assert settings.data_path.is_dir()
    assert {p.name for p in settings.data_path.glob("*.csv")} == {
        "inventory.csv",
        "machines.csv",
        "materials.csv",
        "orders.csv",
        "process.csv",
    }
    assert not list(settings.data_path.glob("*.jsonl"))


def test_explicit_runtime_paths_are_honored(tmp_path: Path) -> None:
    settings = Settings(
        backend=BackendType.MOCK,
        wiki_path=tmp_path / "wiki-explicit",
        log_path=tmp_path / "logs-explicit",
    )
    assert settings.wiki_path == tmp_path / "wiki-explicit"
    assert settings.log_path == tmp_path / "logs-explicit"


def test_all_factory_datasets_load_with_records() -> None:
    loader = DataLoader(FACTORY_DATA)
    expected = {"inventory", "machines", "materials", "orders", "process"}
    assert set(loader.list_datasets()) == expected
    for dataset_name in expected:
        frame = loader.load(dataset_name)
        assert not frame.empty, f"{dataset_name} should contain records"


def test_material_sufficiency_business_result(mock_harness: AgentHarness) -> None:
    response = mock_harness.process_query("Do we have enough fabric for order ORD-1001?")
    result = response["result"]["tool_results"][0]["result"]
    assert response["skill_name"] == "material_sufficiency"
    assert result["order_id"] == "ORD-1001"
    assert result["overall_status"] == "insufficient"


def test_machine_requirements_returns_positive_hours(mock_harness: AgentHarness) -> None:
    response = mock_harness.process_query("What machines are needed for order ORD-1002?")
    result = response["result"]["tool_results"][0]["result"]
    assert response["skill_name"] == "machine_requirements"
    assert result["total_hours"] > 0


def test_write_request_is_rejected(mock_harness: AgentHarness) -> None:
    response = mock_harness.process_query("Delete inventory record FAB-001.")
    assert response["skill_name"] == "security_rejected"
    assert response["warnings"]


def test_api_smoke_in_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    monkeypatch.setenv("BACKEND", "MOCK")
    web_app = importlib.import_module("web_app")
    web_app.initialize_harness()
    dashboard = web_app.dashboard()
    tools = web_app.list_tools()
    chat = web_app.chat(
        web_app.ChatRequest(query="Do we have enough fabric for order ORD-1001?")
    )

    assert dashboard.status_code == 200
    assert json.loads(dashboard.body)["active_orders"] == 8
    assert json.loads(dashboard.body)["machines_operational"] == 5
    assert tools.status_code == 200
    assert any(
        tool["name"] == "check_material_sufficiency"
        for tool in json.loads(tools.body)
    )
    assert chat.skill_name == "material_sufficiency"
