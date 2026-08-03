from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_excel(df: pd.DataFrame, path: Path, sheet_name: str = "Report") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return path
