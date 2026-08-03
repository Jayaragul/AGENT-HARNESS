from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class SchemaViolation(Exception):
    pass


class MissingColumnsError(SchemaViolation):
    def __init__(self, dataset: str, missing: list[str]) -> None:
        self.dataset = dataset
        self.missing = missing
        super().__init__(f"Dataset '{dataset}' missing required columns: {missing}")


class InvalidDateError(SchemaViolation):
    def __init__(self, dataset: str, column: str, row: int, value: Any) -> None:
        self.dataset = dataset
        self.column = column
        self.row = row
        self.value = value
        super().__init__(
            f"Invalid date in '{dataset}.{column}' row {row}: {value!r}"
        )


class DuplicateIdError(SchemaViolation):
    def __init__(self, dataset: str, column: str, value: Any) -> None:
        self.dataset = dataset
        self.column = column
        self.value = value
        super().__init__(f"Duplicate {column} '{value}' in dataset '{dataset}'")


class NullValueError(SchemaViolation):
    def __init__(self, dataset: str, column: str, row: int) -> None:
        self.dataset = dataset
        self.column = column
        self.row = row
        super().__init__(f"Null value in '{dataset}.{column}' row {row}")


class InvalidQuantityError(SchemaViolation):
    def __init__(self, dataset: str, column: str, row: int, value: Any) -> None:
        self.dataset = dataset
        self.column = column
        self.row = row
        self.value = value
        super().__init__(
            f"Invalid quantity in '{dataset}.{column}' row {row}: {value!r}"
        )
        self.value = value


class UnsupportedFileTypeError(SchemaViolation):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Unsupported file type: {path.suffix} for file '{path}'")


class UnitMismatchError(SchemaViolation):
    def __init__(self, dataset: str, expected: str, found: str, row: int) -> None:
        self.dataset = dataset
        self.expected = expected
        self.found = found
        self.row = row
        super().__init__(
            f"Unit mismatch in '{dataset}' row {row}: expected '{expected}', found '{found}'"
        )


class ColumnDef(BaseModel):
    name: str
    dtype: str
    required: bool = True
    primary_key: bool = False
    nullable: bool = False
    unit: str | None = None


class DatasetSchema(BaseModel):
    name: str
    columns: list[ColumnDef]
    allowed_extensions: list[str] = [".csv"]

    def required_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.required]

    def primary_key_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.primary_key]

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(f"Extension must start with '.': {ext}")
        return v


INVENTORY_SCHEMA = DatasetSchema(
    name="inventory",
    columns=[
        ColumnDef(name="item_id", dtype="str", required=True, primary_key=True),
        ColumnDef(name="item_name", dtype="str", required=True),
        ColumnDef(name="category", dtype="str", required=True),
        ColumnDef(name="unit", dtype="str", required=True),
        ColumnDef(name="quantity_on_hand", dtype="float", required=True),
        ColumnDef(name="location", dtype="str", required=False, nullable=True),
        ColumnDef(name="last_updated", dtype="datetime", required=True),
    ],
)

ORDERS_SCHEMA = DatasetSchema(
    name="orders",
    columns=[
        ColumnDef(name="order_id", dtype="str", required=True, primary_key=True),
        ColumnDef(name="product_name", dtype="str", required=True),
        ColumnDef(name="quantity", dtype="float", required=True),
        ColumnDef(name="unit", dtype="str", required=True),
        ColumnDef(name="due_date", dtype="datetime", required=True),
        ColumnDef(name="status", dtype="str", required=True),
        ColumnDef(name="priority", dtype="str", required=True),
        ColumnDef(name="customer", dtype="str", required=False, nullable=True),
    ],
)

PROCESS_SCHEMA = DatasetSchema(
    name="process",
    columns=[
        ColumnDef(name="product_name", dtype="str", required=True),
        ColumnDef(name="material_id", dtype="str", required=True),
        ColumnDef(name="material_name", dtype="str", required=True),
        ColumnDef(name="quantity_per_unit", dtype="float", required=True),
        ColumnDef(name="unit", dtype="str", required=True),
        ColumnDef(name="machine_id", dtype="str", required=True),
        ColumnDef(name="machine_name", dtype="str", required=True),
        ColumnDef(name="setup_time_min", dtype="float", required=True),
        ColumnDef(name="cycle_time_min", dtype="float", required=True),
    ],
)

MACHINES_SCHEMA = DatasetSchema(
    name="machines",
    columns=[
        ColumnDef(name="machine_id", dtype="str", required=True, primary_key=True),
        ColumnDef(name="machine_name", dtype="str", required=True),
        ColumnDef(name="type", dtype="str", required=True),
        ColumnDef(name="status", dtype="str", required=True),
        ColumnDef(name="location", dtype="str", required=False, nullable=True),
        ColumnDef(name="hourly_rate", dtype="float", required=True),
        ColumnDef(name="maintenance_last", dtype="datetime", required=True),
        ColumnDef(name="maintenance_next", dtype="datetime", required=True),
    ],
)

MATERIALS_SCHEMA = DatasetSchema(
    name="materials",
    columns=[
        ColumnDef(name="material_id", dtype="str", required=True, primary_key=True),
        ColumnDef(name="material_name", dtype="str", required=True),
        ColumnDef(name="category", dtype="str", required=True),
        ColumnDef(name="unit", dtype="str", required=True),
        ColumnDef(name="unit_cost", dtype="float", required=True),
        ColumnDef(name="lead_time_days", dtype="int", required=True),
        ColumnDef(name="supplier", dtype="str", required=True),
        ColumnDef(name="min_stock_level", dtype="float", required=True),
    ],
)

DATASET_SCHEMAS: dict[str, DatasetSchema] = {
    "inventory": INVENTORY_SCHEMA,
    "orders": ORDERS_SCHEMA,
    "process": PROCESS_SCHEMA,
    "machines": MACHINES_SCHEMA,
    "materials": MATERIALS_SCHEMA,
}


def get_schema(dataset_name: str) -> DatasetSchema:
    schema = DATASET_SCHEMAS.get(dataset_name)
    if schema is None:
        raise SchemaViolation(f"Unknown dataset: {dataset_name}")
    return schema


def validate_and_normalize(
    df: pd.DataFrame,
    schema: DatasetSchema,
    dataset_name: str | None = None,
) -> pd.DataFrame:
    name = dataset_name or schema.name

    missing = [c for c in schema.required_columns() if c not in df.columns]
    if missing:
        raise MissingColumnsError(name, missing)

    df = df.copy()

    for col_def in schema.columns:
        col = col_def.name
        if col not in df.columns:
            continue

        if col_def.dtype == "datetime":
            df[col] = _normalize_dates(df[col], name, col)
        elif col_def.dtype == "float":
            df[col] = _normalize_numeric(df[col], name, col)
        elif col_def.dtype == "int":
            df[col] = _normalize_integer(df[col], name, col)
        elif col_def.dtype == "str":
            null_mask = df[col].isna()
            df[col] = df[col].astype(str).str.strip()
            df.loc[null_mask, col] = None

    for col_def in schema.columns:
        col = col_def.name
        if col not in df.columns:
            continue

        null_mask = df[col].isna()
        if null_mask.any() and not col_def.nullable:
            first_null = null_mask.idxmax()
            raise NullValueError(name, col, int(first_null) + 2)

    if schema.primary_key_columns():
        pk_cols = schema.primary_key_columns()
        duplicates = df[df.duplicated(subset=pk_cols, keep=False)]
        if not duplicates.empty:
            for pk_col in pk_cols:
                dupes = df[df.duplicated(subset=pk_col, keep=False)]
                if not dupes.empty:
                    raise DuplicateIdError(name, pk_col, dupes.iloc[0][pk_col])

    return df


def _normalize_dates(series: pd.Series, dataset: str, col: str) -> pd.Series:
    result = []
    for idx, val in enumerate(series):
        if pd.isna(val) or str(val).strip() == "":
            result.append(pd.NaT)
            continue
        parsed = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(str(val).strip(), fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise InvalidDateError(dataset, col, idx + 2, val)
        result.append(parsed)
    return pd.Series(result, index=series.index)


def _normalize_numeric(series: pd.Series, dataset: str, col: str) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    mask = result.isna() & series.notna()
    if mask.any():
        first_bad = series[mask].iloc[0]
        bad_idx = series[mask].index[0]
        raise InvalidQuantityError(dataset, col, int(bad_idx) + 2, first_bad)
    return result


def _normalize_integer(series: pd.Series, dataset: str, col: str) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    mask = result.isna() & series.notna()
    if mask.any():
        first_bad = series[mask].iloc[0]
        bad_idx = series[mask].index[0]
        raise InvalidQuantityError(dataset, col, int(bad_idx) + 2, first_bad)
    if not (result.dropna() % 1 == 0).all():
        bad_idx = series[~(result % 1 == 0)].index[0]
        raise InvalidQuantityError(dataset, col, int(bad_idx) + 2, series.iloc[bad_idx])
    return result.astype("Int64")
