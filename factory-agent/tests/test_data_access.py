from pathlib import Path

import pandas as pd
import pytest

from data_access.csv_loader import load_csv, load_dataset
from data_access.loader import DataLoader
from data_access.query_engine import QueryEngine
from data_access.schema_validator import (
    UnsupportedFileTypeError,
    get_schema,
)


def test_load_csv_valid(tmp_path: Path) -> None:
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("col1,col2\n1,2\n3,4", encoding="utf-8")
    df = load_csv(csv_file)
    assert len(df) == 2
    assert list(df.columns) == ["col1", "col2"]


def test_load_csv_column_normalization(tmp_path: Path) -> None:
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Column One,Column Two\n1,2\n", encoding="utf-8")
    df = load_csv(csv_file)
    assert "column_one" in df.columns
    assert "column_two" in df.columns


def test_load_csv_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFileTypeError):
        load_csv(tmp_path / "test.txt")


def test_load_csv_with_schema(tmp_path: Path) -> None:
    csv_file = tmp_path / "inventory.csv"
    csv_file.write_text(
        "item_id,item_name,category,unit,quantity_on_hand,location,last_updated\n"
        "A1,Wood,raw_material,kg,100.0,Warehouse-A,2026-07-23\n",
        encoding="utf-8",
    )
    schema = get_schema("inventory")
    df = load_csv(csv_file, schema)
    assert len(df) == 1
    assert df["item_id"].iloc[0] == "A1"


def test_loader_load(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    inv_file = data_dir / "inventory.csv"
    inv_file.write_text(
        "item_id,item_name,category,unit,quantity_on_hand,location,last_updated\n"
        "A1,Wood,raw_material,kg,100.0,Warehouse-A,2026-07-23\n",
        encoding="utf-8",
    )
    orders_file = data_dir / "orders.csv"
    orders_file.write_text(
        "order_id,product_name,quantity,unit,due_date,status,priority,customer\n"
        "O1,Chair,10,pieces,2026-08-01,active,high,ACME\n",
        encoding="utf-8",
    )

    loader = DataLoader(data_dir)
    df = loader.load("inventory")
    assert len(df) == 1

    datasets = loader.list_datasets()
    assert "inventory" in datasets
    assert "orders" in datasets


def test_query_engine_filter() -> None:
    df = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "a"]})
    result = QueryEngine.filter_by_column(df, "val", "a")
    assert len(result) == 2


def test_query_engine_join() -> None:
    left = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    right = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
    result = QueryEngine.join(left, right, "id")
    assert len(result) == 2
    assert result["val"].iloc[0] == 10


def test_query_engine_group_sum() -> None:
    df = pd.DataFrame({"cat": ["x", "x", "y"], "val": [1.0, 2.0, 3.0]})
    result = QueryEngine.group_sum(df, "cat", "val")
    assert result[result["cat"] == "x"]["val"].iloc[0] == 3.0
