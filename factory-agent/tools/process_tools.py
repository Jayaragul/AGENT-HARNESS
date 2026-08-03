from __future__ import annotations

import pandas as pd


def get_bom_for_product(df: pd.DataFrame, product_name: str) -> pd.DataFrame:
    bom = df[df["product_name"] == product_name].copy()
    if bom.empty:
        raise ValueError(f"Product '{product_name}' not found in process data")
    return bom


def get_materials_for_product(df: pd.DataFrame, product_name: str) -> pd.DataFrame:
    return get_bom_for_product(df, product_name)[
        ["material_id", "material_name", "quantity_per_unit", "unit"]
    ].drop_duplicates(subset=["material_id"])


def get_machines_for_product(df: pd.DataFrame, product_name: str) -> pd.DataFrame:
    return get_bom_for_product(df, product_name)[
        ["machine_id", "machine_name", "setup_time_min", "cycle_time_min"]
    ].drop_duplicates(subset=["machine_id"])


def get_total_material_requirement(
    bom_df: pd.DataFrame, order_quantity: float
) -> pd.DataFrame:
    result = bom_df.copy()
    result["total_required"] = result["quantity_per_unit"] * order_quantity
    return result
