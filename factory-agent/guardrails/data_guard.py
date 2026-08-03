from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd


class DataValidationError(Exception):
    pass


class StaleDataError(DataValidationError):
    pass


class MissingColumnError(DataValidationError):
    pass


class UnitValidationError(DataValidationError):
    pass


class DataGuard:
    @staticmethod
    def check_staleness(
        df: pd.DataFrame, date_column: str, max_age_days: int = 7
    ) -> None:
        if date_column not in df.columns:
            raise MissingColumnError(f"Column '{date_column}' not found")
        if df.empty:
            return
        latest = df[date_column].max()
        if isinstance(latest, str):
            latest = datetime.fromisoformat(latest)
        age = datetime.now() - latest
        if age > timedelta(days=max_age_days):
            raise StaleDataError(
                f"Data in column '{date_column}' is {age.days} days old "
                f"(max allowed: {max_age_days} days)"
            )

    @staticmethod
    def validate_columns(df: pd.DataFrame, required: list[str]) -> None:
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise MissingColumnError(f"Missing columns: {missing}")

    @staticmethod
    def validate_identifier(value: str, pattern: str = r"^[A-Za-z0-9_\-]+$") -> None:
        import re

        if not re.match(pattern, str(value)):
            raise DataValidationError(f"Invalid identifier format: '{value}'")

    @staticmethod
    def validate_date(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    return datetime.strptime(value.strip(), fmt)
                except ValueError:
                    continue
        raise DataValidationError(f"Invalid date value: '{value}'")

    @staticmethod
    def validate_quantity(value: Any) -> float:
        try:
            qty = float(value)
        except (ValueError, TypeError):
            raise DataValidationError(f"Invalid quantity: '{value}'")
        if qty < 0:
            raise DataValidationError(f"Negative quantity: {qty}")
        return qty

    @staticmethod
    def validate_unit(value: str, expected_units: list[str]) -> None:
        unit = str(value).strip().lower()
        expected = [u.lower() for u in expected_units]
        if unit not in expected:
            raise UnitValidationError(
                f"Unit '{value}' not in expected units: {expected_units}"
            )
