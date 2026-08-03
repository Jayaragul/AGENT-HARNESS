from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_access.schema_validator import (
    DatasetSchema,
    UnsupportedFileTypeError,
    get_schema,
    validate_and_normalize,
)


def load_csv(path: Path, schema: DatasetSchema | None = None) -> pd.DataFrame:
    if path.suffix.lower() not in (".csv",):
        raise UnsupportedFileTypeError(path)

    df = pd.read_csv(path, dtype_backend="numpy_nullable")

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    if schema:
        df = validate_and_normalize(df, schema)

    return df


def load_dataset(
    data_dir: Path,
    dataset_name: str,
) -> pd.DataFrame:
    schema = get_schema(dataset_name)
    csv_path = data_dir / f"{dataset_name}.csv"

    if not csv_path.exists():
        alt_path = data_dir / f"{dataset_name}.CSV"
        if alt_path.exists():
            csv_path = alt_path
        else:
            raise FileNotFoundError(
                f"Dataset '{dataset_name}' not found at {csv_path}"
            )

    return load_csv(csv_path, schema)
