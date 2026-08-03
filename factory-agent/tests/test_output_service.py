from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

from output_service.writer import Writer
from output_service.csv_writer import write_csv
from output_service.json_writer import write_json
from output_service.output_registry import OutputRegistry


def test_write_csv(tmp_path: Path) -> None:
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    path = tmp_path / "test.csv"
    result = write_csv(df, path)
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "col1" in content


def test_write_json(tmp_path: Path) -> None:
    data = {"key": "value", "number": 42}
    path = tmp_path / "test.json"
    result = write_json(data, path)
    assert result.exists()
    import json
    loaded = json.loads(result.read_text(encoding="utf-8"))
    assert loaded["key"] == "value"


def test_writer_csv(tmp_path: Path) -> None:
    writer = Writer(tmp_path / "outputs")
    df = pd.DataFrame({"a": [1], "b": [2]})
    path = writer.write_report(
        data=df,
        report_name="test_report",
        skill_name="test_skill",
        source_datasets=["inventory"],
        query="test query",
        result_summary="summary",
        fmt="csv",
    )
    assert path.exists()
    assert path.suffix == ".csv"


def test_writer_json(tmp_path: Path) -> None:
    writer = Writer(tmp_path / "outputs")
    data = {"result": "test"}
    path = writer.write_report(
        data=data,
        report_name="test_json",
        skill_name="test",
        source_datasets=[],
        query="query",
        fmt="json",
    )
    assert path.exists()
    assert path.suffix == ".json"


def test_output_registry(tmp_path: Path) -> None:
    registry = OutputRegistry(tmp_path)
    entry = registry.register(
        report_name="test",
        file_path=tmp_path / "test.csv",
        skill_name="skill",
        query="query",
        result_summary="summary",
        source_datasets=["data"],
        warnings=[],
        audit_id="abc123",
    )
    assert entry["audit_id"] == "abc123"
    assert len(registry.list_outputs()) == 1
