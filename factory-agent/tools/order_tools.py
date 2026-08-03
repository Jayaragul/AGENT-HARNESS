from __future__ import annotations

import pandas as pd


def get_order(df: pd.DataFrame, order_id: str) -> pd.DataFrame:
    row = df[df["order_id"] == order_id]
    if row.empty:
        raise ValueError(f"Order '{order_id}' not found")
    return row


def get_active_orders(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "active"].copy()


def get_orders_by_priority(df: pd.DataFrame, priority: str) -> pd.DataFrame:
    return df[df["priority"] == priority].copy()


def get_order_product_quantity(df: pd.DataFrame, order_id: str) -> tuple[str, float]:
    row = get_order(df, order_id)
    return str(row["product_name"].iloc[0]), float(row["quantity"].iloc[0])
