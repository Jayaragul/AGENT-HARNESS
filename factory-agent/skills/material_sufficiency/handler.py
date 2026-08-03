from __future__ import annotations

from typing import Any

import pandas as pd

from data_access.loader import DataLoader
from tools import calculation_tools, inventory_tools, order_tools, process_tools


def handle_material_sufficiency(
    loader: DataLoader, order_id: str
) -> dict[str, Any]:
    orders_df = loader.load("orders")
    order_row = order_tools.get_order(orders_df, order_id)
    order = order_row.iloc[0]

    if order["status"] != "active":
        return {
            "skill": "material_sufficiency",
            "order_id": order_id,
            "error": f"Order '{order_id}' has status '{order['status']}', not 'active'",
        }

    product_name = order["product_name"]
    order_quantity = float(order["quantity"])
    order_unit = order["unit"]

    process_df = loader.load("process")
    bom = process_tools.get_materials_for_product(process_df, product_name)
    total_req = process_tools.get_total_material_requirement(bom, order_quantity)

    inventory_df = loader.load("inventory")

    materials_result: list[dict[str, Any]] = []
    overall_insufficient = False

    for _, row in total_req.iterrows():
        material_id = row["material_id"]
        material_name = row["material_name"]
        required = float(row["total_required"])
        unit = row["unit"]

        try:
            available = inventory_tools.get_item_quantity(inventory_df, material_id)
        except ValueError:
            available = 0.0

        shortage = calculation_tools.subtract(required, available)
        if shortage < 0:
            shortage = 0.0

        status = "sufficient" if available >= required else "insufficient"
        if status == "insufficient":
            overall_insufficient = True

        materials_result.append(
            {
                "material_id": material_id,
                "material_name": material_name,
                "required": required,
                "available": available,
                "shortage": round(shortage, 2) if status == "insufficient" else 0.0,
                "unit": unit,
                "status": status,
            }
        )

    last_updated = None
    if "last_updated" in inventory_df.columns and not inventory_df.empty:
        last_updated = str(inventory_df["last_updated"].max())

    return {
        "skill": "material_sufficiency",
        "order_id": order_id,
        "product_name": product_name,
        "order_quantity": order_quantity,
        "order_unit": order_unit,
        "overall_status": "insufficient" if overall_insufficient else "sufficient",
        "materials": materials_result,
        "data_last_updated": last_updated,
        "recommendation": _generate_recommendation(materials_result),
    }


def _generate_recommendation(
    materials: list[dict[str, Any]],
) -> str:
    shortages = [
        m for m in materials if m["status"] == "insufficient" and m["shortage"] > 0
    ]
    if not shortages:
        return "All materials are available. Proceed with production."
    parts = [
        f"Purchase or reallocate {s['shortage']} {s['unit']} of {s['material_name']}."
        for s in shortages
    ]
    return " ".join(parts)
