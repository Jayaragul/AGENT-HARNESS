from __future__ import annotations

from datetime import datetime
from typing import Any

from data_access.loader import DataLoader
from tools import calculation_tools, inventory_tools, order_tools, process_tools


def handle_material_risk_report(loader: DataLoader) -> dict[str, Any]:
    orders_df = loader.load("orders")
    active_orders = order_tools.get_active_orders(orders_df)

    if active_orders.empty:
        return {
            "skill": "material_risk_report",
            "generated_at": datetime.now().isoformat(),
            "total_active_orders": 0,
            "materials_at_risk": [],
            "summary": {
                "total_materials_at_risk": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            },
        }

    process_df = loader.load("process")
    inventory_df = loader.load("inventory")
    materials_df = loader.load("materials")

    material_demand: dict[str, dict[str, Any]] = {}

    for _, order in active_orders.iterrows():
        order_id = order["order_id"]
        product_name = order["product_name"]
        order_quantity = float(order["quantity"])

        try:
            bom = process_tools.get_bom_for_product(process_df, product_name)
        except ValueError:
            continue

        req = process_tools.get_total_material_requirement(bom, order_quantity)

        for _, row in req.iterrows():
            mid = row["material_id"]
            qty = float(row["total_required"])
            unit = row["unit"]
            mat_name = row["material_name"]

            if mid not in material_demand:
                try:
                    available = inventory_tools.get_item_quantity(inventory_df, mid)
                except ValueError:
                    available = 0.0

                min_stock = 0.0
                lead_time = 0
                supplier = ""
                unit_cost = 0.0
                mat_ref = materials_df[materials_df["material_id"] == mid]
                if not mat_ref.empty:
                    m = mat_ref.iloc[0]
                    lead_time = int(m["lead_time_days"]) if "lead_time_days" in m else 0
                    supplier = str(m["supplier"]) if "supplier" in m else ""
                    unit_cost = float(m["unit_cost"]) if "unit_cost" in m else 0.0
                    min_stock = float(m["min_stock_level"]) if "min_stock_level" in m else 0.0

                material_demand[mid] = {
                    "material_id": mid,
                    "material_name": mat_name,
                    "total_required": 0.0,
                    "total_available": available,
                    "unit": unit,
                    "affected_orders": [],
                    "lead_time_days": lead_time,
                    "supplier": supplier,
                    "unit_cost": unit_cost,
                    "min_stock_level": min_stock,
                }

            material_demand[mid]["total_required"] += qty
            material_demand[mid]["affected_orders"].append(order_id)

    materials_at_risk: list[dict[str, Any]] = []
    for mid, data in material_demand.items():
        shortage = calculation_tools.subtract(
            data["total_required"], data["total_available"]
        )
        if shortage < 0:
            shortage = 0.0

        below_min_stock = data["total_available"] < data["min_stock_level"]

        if shortage <= 0 and not below_min_stock:
            continue

        risk_score = shortage * data["lead_time_days"]

        if risk_score > 100:
            risk_level = "critical"
        elif risk_score > 30:
            risk_level = "high"
        elif risk_score > 5:
            risk_level = "medium"
        else:
            risk_level = "low"

        materials_at_risk.append(
            {
                "material_id": mid,
                "material_name": data["material_name"],
                "total_required": round(data["total_required"], 2),
                "total_available": round(data["total_available"], 2),
                "total_shortage": round(shortage, 2),
                "unit": data["unit"],
                "affected_orders": list(dict.fromkeys(data["affected_orders"])),
                "lead_time_days": data["lead_time_days"],
                "supplier": data["supplier"],
                "unit_cost": data["unit_cost"],
                "risk_score": round(risk_score, 2),
                "risk_level": risk_level,
            }
        )

    materials_at_risk.sort(key=lambda x: x["risk_score"], reverse=True)

    summary = {"total_materials_at_risk": len(materials_at_risk)}
    for level in ("critical", "high", "medium", "low"):
        summary[level] = sum(1 for m in materials_at_risk if m["risk_level"] == level)

    return {
        "skill": "material_risk_report",
        "generated_at": datetime.now().isoformat(),
        "total_active_orders": len(active_orders),
        "materials_at_risk": materials_at_risk,
        "summary": summary,
    }
