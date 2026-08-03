from __future__ import annotations

import pandas as pd


def get_item_quantity(df: pd.DataFrame, item_id: str) -> float:
    row = df[df["item_id"] == item_id]
    if row.empty:
        raise ValueError(f"Item '{item_id}' not found in inventory")
    return float(row["quantity_on_hand"].iloc[0])


def get_items_by_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
    return df[df["category"] == category].copy()


def get_items_below_threshold(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    return df[df["quantity_on_hand"] < threshold].copy()


def get_all_item_quantities(df: pd.DataFrame) -> dict[str, float]:
    return dict(zip(df["item_id"], df["quantity_on_hand"]))
