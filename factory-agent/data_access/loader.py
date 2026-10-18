from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from data_access.csv_loader import load_dataset
from data_access.revision import (
    DataRevision,
    DataRevisionChangedError,
    calculate_data_revision,
)
from data_access.schema_validator import DATASET_SCHEMAS


class DataLoader:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._cache: dict[str, pd.DataFrame] = {}
        self._pinned_revision = calculate_data_revision(data_dir)

    @property
    def revision(self) -> DataRevision:
        current = calculate_data_revision(self._data_dir)
        if current.revision_id != self._pinned_revision.revision_id:
            raise DataRevisionChangedError(
                "Factory data changed while the agent was running. Restart the "
                "service to load and validate one consistent data revision."
            )
        return self._pinned_revision

    def load(self, dataset_name: str) -> pd.DataFrame:
        self.revision
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
