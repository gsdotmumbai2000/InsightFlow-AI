"""Presentation-only formatting helpers (no business rules)."""

from __future__ import annotations

from datetime import datetime


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def display_or_dash(value: str | None) -> str:
    text = (value or "").strip()
    return text if text else "—"
