from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from agent.context_builder import ContextBuilder
from data_access.loader import DataLoader
from skills.machine_requirements.handler import handle_machine_requirements
from skills.material_risk_report.handler import handle_material_risk_report
from skills.material_sufficiency.handler import handle_material_sufficiency
from tools import inventory_tools, order_tools, process_tools


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


class ToolExecutionError(Exception):
    pass


class ToolInputError(ToolExecutionError):
    pass


class ToolRegistry:
    def __init__(
        self,
        loader: DataLoader,
        context_builder: ContextBuilder,
    ) -> None:
        self._loader = loader
        self._context_builder = context_builder
        self._tools: dict[str, Callable[..., dict[str, Any]]] = {
            "list_available_datasets": self.list_available_datasets,
            "describe_dataset": self.describe_dataset,
            "query_orders": self.query_orders,
            "get_order": self.get_order,
            "get_inventory_item": self.get_inventory_item,
            "get_product_process": self.get_product_process,
            "check_material_sufficiency": self.check_material_sufficiency,
            "get_machine_requirements": self.get_machine_requirements,
            "generate_material_risk_report": self.generate_material_risk_report,
        }

    def definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="list_available_datasets",
                description="List approved read-only factory datasets.",
                parameters={},
            ),
            ToolDefinition(
                name="describe_dataset",
                description="Describe one approved dataset using its schema and catalog wiki.",
                parameters={"dataset_name": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="query_orders",
                description="List orders with optional status or priority filters.",
                parameters={
                    "status": {"type": "string", "required": False},
                    "priority": {"type": "string", "required": False},
                    "limit": {"type": "integer", "required": False},
                },
            ),
            ToolDefinition(
                name="get_order",
                description="Get verified details for a single order ID such as ORD-1001.",
                parameters={"order_id": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="get_inventory_item",
                description="Get verified inventory details for a material/item ID such as FAB-001.",
                parameters={"material_id": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="get_product_process",
                description="Get material and machine process rows for a product name.",
                parameters={"product_name": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="check_material_sufficiency",
                description="Calculate deterministic material sufficiency for an order ID.",
                parameters={"order_id": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="get_machine_requirements",
                description="Calculate deterministic machine hours and cost for an order ID.",
                parameters={"order_id": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="generate_material_risk_report",
                description="Calculate deterministic material risk across all active orders.",
                parameters={},
            ),
        ]

    def list_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if name not in self._tools:
            raise ToolExecutionError(f"Tool '{name}' is not approved.")
        validated = self._validate_arguments(name, arguments or {})
        try:
            return self._tools[name](**validated)
        except ToolExecutionError:
            raise
        except (TypeError, ValueError) as exc:
            raise ToolExecutionError(f"Tool '{name}' failed: {exc}") from exc

    def _validate_arguments(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ToolInputError(f"Tool '{name}' arguments must be an object.")

        definition = next(item for item in self.definitions() if item.name == name)
        unknown = sorted(set(arguments) - set(definition.parameters))
        if unknown:
            raise ToolInputError(
                f"Tool '{name}' received unknown arguments: {', '.join(unknown)}"
            )

        missing = [
            key
            for key, spec in definition.parameters.items()
            if spec.get("required") and key not in arguments
        ]
        if missing:
            raise ToolInputError(
                f"Tool '{name}' is missing required arguments: {', '.join(missing)}"
            )

        expected_types = {"string": str, "integer": int, "number": (int, float)}
        validated = dict(arguments)
        for key, value in validated.items():
            expected_name = definition.parameters[key].get("type")
            expected = expected_types.get(expected_name)
            if expected and (not isinstance(value, expected) or isinstance(value, bool)):
                raise ToolInputError(
                    f"Tool '{name}' argument '{key}' must be {expected_name}."
                )

        for identifier in ("order_id", "material_id"):
            if identifier in validated:
                validated[identifier] = validated[identifier].replace("_", "-").upper()

        if "limit" in validated and not 1 <= validated["limit"] <= 100:
            raise ToolInputError("Tool 'query_orders' limit must be between 1 and 100.")

        return validated

    def list_available_datasets(self) -> dict[str, Any]:
        return {"datasets": self._loader.list_datasets()}

    def describe_dataset(self, dataset_name: str) -> dict[str, Any]:
        schema = self._loader.get_schema(dataset_name)
        catalog = self._context_builder.load_catalog(f"{dataset_name}.md")
        return {
            "dataset_name": dataset_name,
            "schema": schema,
            "catalog": catalog,
        }

    def query_orders(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        orders = self._loader.load("orders")
        if status:
            orders = orders[orders["status"] == status]
        if priority:
            orders = orders[orders["priority"] == priority]
        return {
            "orders": self._records(orders.head(limit)),
            "count": int(len(orders)),
        }

    def get_order(self, order_id: str) -> dict[str, Any]:
        orders = self._loader.load("orders")
        order = order_tools.get_order(orders, order_id)
        return {"order": self._records(order)[0]}

    def get_inventory_item(self, material_id: str) -> dict[str, Any]:
        inventory = self._loader.load("inventory")
        row = inventory[inventory["item_id"] == material_id]
        if row.empty:
            raise ValueError(f"Inventory item '{material_id}' not found")
        quantity = inventory_tools.get_item_quantity(inventory, material_id)
        item = self._records(row)[0]
        item["quantity_on_hand"] = quantity
        return {"inventory_item": item}

    def get_product_process(self, product_name: str) -> dict[str, Any]:
        process = self._loader.load("process")
        bom = process_tools.get_bom_for_product(process, product_name)
        return {"product_name": product_name, "process_rows": self._records(bom)}

    def check_material_sufficiency(self, order_id: str) -> dict[str, Any]:
        return handle_material_sufficiency(self._loader, order_id)

    def get_machine_requirements(self, order_id: str) -> dict[str, Any]:
        return handle_machine_requirements(self._loader, order_id)

    def generate_material_risk_report(self) -> dict[str, Any]:
        return handle_material_risk_report(self._loader)

    def _records(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        clean = df.astype(object).where(pd.notna(df), None)
        return clean.to_dict(orient="records")
