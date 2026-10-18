from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from data_access.schema_validator import DATASET_SCHEMAS


REVISION_FORMAT = "factory-data-sha256-v1"


class DataRevisionChangedError(RuntimeError):
    """Raised when source data changes after a process pins its revision."""


@dataclass(frozen=True)
class DataRevision:
    revision_id: str
    format: str
    datasets: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.revision_id,
            "format": self.format,
            "datasets": list(self.datasets),
        }


def calculate_data_revision(data_dir: Path) -> DataRevision:
    """Fingerprint canonical CSV bytes and their executable schema contracts.

    The revision records hashes and dataset names only; it never copies or
    exposes factory rows. Missing files are represented explicitly so a
    partially provisioned bundle cannot be mistaken for a complete one.
    """
    records: list[dict[str, object]] = []
    for name in sorted(DATASET_SCHEMAS):
        schema = DATASET_SCHEMAS[name]
        schema_payload = json.dumps(
            schema.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        path = _dataset_path(data_dir, name)
        source_hash = _file_sha256(path) if path is not None else None
        records.append(
            {
                "name": name,
                "schema_sha256": hashlib.sha256(schema_payload).hexdigest(),
                "source_sha256": source_hash,
            }
        )

    payload = json.dumps(records, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{REVISION_FORMAT}\n{payload}".encode("utf-8")).hexdigest()
    return DataRevision(
        revision_id=f"{REVISION_FORMAT}:{digest}",
        format=REVISION_FORMAT,
        datasets=tuple(sorted(DATASET_SCHEMAS)),
    )


def _dataset_path(data_dir: Path, dataset: str) -> Path | None:
    for suffix in (".csv", ".CSV"):
        candidate = data_dir / f"{dataset}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
