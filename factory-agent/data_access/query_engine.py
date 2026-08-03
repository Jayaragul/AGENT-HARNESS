from __future__ import annotations

import pandas as pd


class QueryEngine:
    @staticmethod
    def filter_by_column(
        df: pd.DataFrame, column: str, value: object
    ) -> pd.DataFrame:
        return df[df[column] == value].copy()

    @staticmethod
    def filter_by_columns(
        df: pd.DataFrame, conditions: dict[str, object]
    ) -> pd.DataFrame:
        result = df.copy()
        for col, val in conditions.items():
            result = result[result[col] == val]
        return result

    @staticmethod
    def join(
        left: pd.DataFrame,
        right: pd.DataFrame,
        left_on: str,
        right_on: str | None = None,
        how: str = "inner",
    ) -> pd.DataFrame:
        right_on = right_on or left_on
        return left.merge(right, left_on=left_on, right_on=right_on, how=how)

    @staticmethod
    def group_sum(
        df: pd.DataFrame, by: str | list[str], value_column: str
    ) -> pd.DataFrame:
        return df.groupby(by)[value_column].sum().reset_index()

    @staticmethod
    def sum_column(df: pd.DataFrame, column: str) -> float:
        return float(df[column].sum())

    @staticmethod
    def multiply_columns(df: pd.DataFrame, col_a: str, col_b: str) -> pd.Series:
        return df[col_a] * df[col_b]
