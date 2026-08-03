from __future__ import annotations

from typing import Any

from data_access.loader import DataLoader
from tools import machine_tools, order_tools, process_tools


def handle_machine_requirements(
    loader: DataLoader, order_id: str
) -> dict[str, Any]:
    orders_df = loader.load("orders")
    order_row = order_tools.get_order(orders_df, order_id)
    order = order_row.iloc[0]

    if order["status"] != "active":
        return {
            "skill": "machine_requirements",
            "order_id": order_id,
            "error": f"Order '{order_id}' has status '{order['status']}', not 'active'",
        }

    product_name = order["product_name"]
    order_quantity = float(order["quantity"])

    process_df = loader.load("process")
    machines = process_tools.get_machines_for_product(process_df, product_name)

    machines_df = loader.load("machines")

    warnings: list[str] = []
    machine_results: list[dict[str, Any]] = []
    total_hours = 0.0
    total_cost = 0.0

    for _, row in machines.iterrows():
        machine_id = row["machine_id"]
        setup_time = float(row["setup_time_min"])
        cycle_time = float(row["cycle_time_min"])

        hours = machine_tools.calculate_machine_hours(
            setup_time, cycle_time, order_quantity
        )

        try:
            machine_info = machine_tools.get_machine(machines_df, machine_id)
            m_row = machine_info.iloc[0]
            status = m_row["status"]
            hourly_rate = float(m_row["hourly_rate"])
        except ValueError:
            status = "unknown"
            hourly_rate = 0.0
            warnings.append(f"Machine '{machine_id}' not found in machines dataset")

        if status in ("maintenance", "offline"):
            warnings.append(
                f"Machine '{machine_id}' is '{status}'. "
                f"Schedule may need adjustment."
            )

        cost = hours["total_hours"] * hourly_rate
        total_hours += hours["total_hours"]
        total_cost += cost

        machine_results.append(
            {
                "machine_id": machine_id,
                "machine_name": row["machine_name"],
                "status": status,
                "setup_hours": round(hours["setup_minutes"] / 60, 2),
                "cycle_hours": round(hours["cycle_minutes"] / 60, 2),
                "total_hours": round(hours["total_hours"], 2),
                "hourly_rate": hourly_rate,
                "estimated_cost": round(cost, 2),
            }
        )

    result: dict[str, Any] = {
        "skill": "machine_requirements",
        "order_id": order_id,
        "product_name": product_name,
        "order_quantity": order_quantity,
        "machines": machine_results,
        "total_hours": round(total_hours, 2),
        "total_cost": round(total_cost, 2),
    }

    if warnings:
        result["warnings"] = warnings

    return result
