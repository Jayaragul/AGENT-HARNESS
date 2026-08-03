from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def write_json(data: Any, path: Path, indent: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)
    return path
