"""Shared serialization helpers for SQLite persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from insightflow.application.exceptions import DataMappingError


def datetime_to_db(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise DataMappingError("Cannot persist a naive datetime.")
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def datetime_from_db(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DataMappingError(
            f"Invalid datetime value in database: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def bool_to_db(value: bool) -> int:
    return 1 if value else 0


def bool_from_db(value: object) -> bool:
    return bool(value)


def json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise DataMappingError(f"Unable to serialize JSON value: {exc}") from exc


def json_loads(value: str | None, *, field_name: str) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise DataMappingError(
            f"Malformed JSON in database field '{field_name}': {exc}"
        ) from exc
