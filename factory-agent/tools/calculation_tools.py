from __future__ import annotations

from datetime import datetime, date
from typing import Any


def subtract(a: float, b: float) -> float:
    return a - b


def add(a: float, b: float) -> float:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


def percentage(part: float, total: float) -> float:
    if total == 0:
        return 0.0
    return (part / total) * 100


def days_until(target_date: date | datetime) -> int:
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    delta = target_date - date.today()
    return delta.days


def format_currency(amount: float, currency: str = "USD") -> str:
    return f"{currency} {amount:,.2f}"


def coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot coerce {value!r} to float")
