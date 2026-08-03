from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from data_access.csv_loader import load_dataset
from data_access.schema_validator import DATASET_SCHEMAS


class DataLoader:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._cache: dict[str, pd.DataFrame] = {}

    def load(self, dataset_name: str) -> pd.DataFrame:
        if dataset_name not in DATASET_SCHEMAS:
            raise ValueError(f"Unknown dataset: {dataset_name}")
        if dataset_name in self._cache:
            return self._cache[dataset_name]
        df = load_dataset(self._data_dir, dataset_name)
        self._cache[dataset_name] = df
        return df

    def get_schema(self, dataset_name: str) -> dict[str, Any]:
        schema = DATASET_SCHEMAS.get(dataset_name)
        if schema is None:
            raise ValueError(f"Unknown dataset: {dataset_name}")
        return schema.model_dump()

    def list_datasets(self) -> list[str]:
        return list(DATASET_SCHEMAS.keys())

    def clear_cache(self) -> None:
        self._cache.clear()
