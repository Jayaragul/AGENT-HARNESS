from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from data_access.schema_validator import (
    DuplicateIdError,
    InvalidDateError,
    InvalidQuantityError,
    MissingColumnsError,
    NullValueError,
    SchemaViolation,
    UnsupportedFileTypeError,
    UnitMismatchError,
    get_schema,
    validate_and_normalize,
)
from data_access.csv_loader import load_csv


class TestSchemaValidation:
    def test_missing_columns_raises_error(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame({"item_id": ["A1"], "item_name": ["Wood"]})
        with pytest.raises(MissingColumnsError) as exc:
            validate_and_normalize(df, schema)
        assert "category" in str(exc.value)
        assert "unit" in str(exc.value)

    def test_invalid_date_raises_error(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1"],
                "item_name": ["Wood"],
                "category": ["raw_material"],
                "unit": ["kg"],
                "quantity_on_hand": [100.0],
                "location": ["A1"],
                "last_updated": ["not-a-date"],
            }
        )
        with pytest.raises(InvalidDateError):
            validate_and_normalize(df, schema)

    def test_valid_date_formats(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1"],
                "item_name": ["Wood"],
                "category": ["raw_material"],
                "unit": ["kg"],
                "quantity_on_hand": [100.0],
                "location": ["A1"],
                "last_updated": ["2026-07-23"],
            }
        )
        result = validate_and_normalize(df, schema)
        assert result["last_updated"].iloc[0] == datetime(2026, 7, 23)

    def test_alternate_date_formats(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1"],
                "item_name": ["Wood"],
                "category": ["raw_material"],
                "unit": ["kg"],
                "quantity_on_hand": [100.0],
                "location": ["A1"],
                "last_updated": ["23-07-2026"],
            }
        )
        result = validate_and_normalize(df, schema)
        assert result["last_updated"].iloc[0] == datetime(2026, 7, 23)

    def test_duplicate_ids_raises_error(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1", "A1"],
                "item_name": ["Wood", "Wood"],
                "category": ["raw_material", "raw_material"],
                "unit": ["kg", "kg"],
                "quantity_on_hand": [100.0, 200.0],
                "location": ["A1", "A1"],
                "last_updated": ["2026-07-23", "2026-07-23"],
            }
        )
        with pytest.raises(DuplicateIdError):
            validate_and_normalize(df, schema)

    def test_null_value_in_required_column_raises_error(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1"],
                "item_name": [None],
                "category": ["raw_material"],
                "unit": ["kg"],
                "quantity_on_hand": [100.0],
                "location": ["A1"],
                "last_updated": ["2026-07-23"],
            }
        )
        with pytest.raises(NullValueError):
            validate_and_normalize(df, schema)

    def test_invalid_quantity_raises_error(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1"],
                "item_name": ["Wood"],
                "category": ["raw_material"],
                "unit": ["kg"],
                "quantity_on_hand": ["not-a-number"],
                "location": ["A1"],
                "last_updated": ["2026-07-23"],
            }
        )
        with pytest.raises(InvalidQuantityError):
            validate_and_normalize(df, schema)

    def test_valid_data_passes_validation(self) -> None:
        schema = get_schema("inventory")
        df = pd.DataFrame(
            {
                "item_id": ["A1", "A2"],
                "item_name": ["Wood", "Steel"],
                "category": ["raw_material", "raw_material"],
                "unit": ["kg", "kg"],
                "quantity_on_hand": [100.0, 200.0],
                "location": ["A1", "B2"],
                "last_updated": ["2026-07-23", "2026-07-23"],
            }
        )
        result = validate_and_normalize(df, schema)
        assert len(result) == 2

    def test_unsupported_file_type(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            load_csv(Path("data.txt"), get_schema("inventory"))

    def test_unknown_dataset_raises_error(self) -> None:
        with pytest.raises(SchemaViolation):
            get_schema("nonexistent")

    def test_orders_schema_validation(self) -> None:
        schema = get_schema("orders")
        df = pd.DataFrame(
            {
                "order_id": ["ORD-001"],
                "product_name": ["Table"],
                "quantity": [100],
                "unit": ["pieces"],
                "due_date": ["2026-08-01"],
                "status": ["active"],
                "priority": ["high"],
                "customer": ["ACME Corp"],
            }
        )
        result = validate_and_normalize(df, schema)
        assert result["order_id"].iloc[0] == "ORD-001"

    def test_process_schema_validation(self) -> None:
        schema = get_schema("process")
        df = pd.DataFrame(
            {
                "product_name": ["Chair"],
                "material_id": ["FAB-001"],
                "material_name": ["Fabric"],
                "quantity_per_unit": [2.5],
                "unit": ["metres"],
                "machine_id": ["CUT-001"],
                "machine_name": ["Cutting Machine"],
                "setup_time_min": [30.0],
                "cycle_time_min": [5.0],
            }
        )
        result = validate_and_normalize(df, schema)
        assert len(result) == 1

    def test_machines_schema_validation(self) -> None:
        schema = get_schema("machines")
        df = pd.DataFrame(
            {
                "machine_id": ["SAW-001"],
                "machine_name": ["Table Saw"],
                "type": ["cutting"],
                "status": ["operational"],
                "location": ["Floor A"],
                "hourly_rate": [50.0],
                "maintenance_last": ["2026-06-01"],
                "maintenance_next": ["2026-09-01"],
            }
        )
        result = validate_and_normalize(df, schema)
        assert result["machine_id"].iloc[0] == "SAW-001"
