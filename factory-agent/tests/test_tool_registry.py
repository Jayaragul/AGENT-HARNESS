from __future__ import annotations

from pathlib import Path

import pytest

from agent.context_builder import ContextBuilder
from agent.tool_registry import ToolInputError, ToolRegistry
from config.settings import Settings
from data_access.loader import DataLoader


@pytest.fixture
def registry() -> ToolRegistry:
    settings = Settings(backend="MOCK")
    return ToolRegistry(
        DataLoader(settings.data_path),
        ContextBuilder(settings.data_catalog_path),
    )


def test_missing_required_argument_is_rejected(registry: ToolRegistry) -> None:
    with pytest.raises(ToolInputError, match="missing required"):
        registry.execute("get_order", {})


def test_unknown_argument_is_rejected(registry: ToolRegistry) -> None:
    with pytest.raises(ToolInputError, match="unknown arguments"):
        registry.execute("get_order", {"order_id": "ORD-1001", "sql": "DROP"})


def test_identifier_is_normalized(registry: ToolRegistry) -> None:
    result = registry.execute("get_order", {"order_id": "ord_1001"})
    assert result["order"]["order_id"] == "ORD-1001"


def test_query_limit_is_bounded(registry: ToolRegistry) -> None:
    with pytest.raises(ToolInputError, match="between 1 and 100"):
        registry.execute("query_orders", {"limit": 1000})
