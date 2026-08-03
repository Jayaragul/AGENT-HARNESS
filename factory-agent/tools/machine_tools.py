from __future__ import annotations

import pandas as pd


def get_machine(df: pd.DataFrame, machine_id: str) -> pd.DataFrame:
    row = df[df["machine_id"] == machine_id]
    if row.empty:
        raise ValueError(f"Machine '{machine_id}' not found")
    return row


def get_operational_machines(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "operational"].copy()


def calculate_machine_hours(
    setup_time_min: float,
    cycle_time_min: float,
    order_quantity: float,
    batch_size: float = 1,
) -> dict[str, float]:
    num_batches = order_quantity / batch_size
    total_setup = setup_time_min * num_batches
    total_cycle = cycle_time_min * order_quantity
    total_minutes = total_setup + total_cycle
    total_hours = total_minutes / 60
    return {
        "setup_minutes": total_setup,
        "cycle_minutes": total_cycle,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
    }
