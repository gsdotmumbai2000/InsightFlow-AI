"""Ensure provider-neutral source rows exist for FK integrity."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from insightflow.domain import SourceType
from insightflow.infrastructure.database.serialization import datetime_to_db


def ensure_source(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    source_type: SourceType | str,
    name: str | None = None,
) -> None:
    """Insert a sources row when missing (idempotent)."""
    existing = connection.execute(
        "SELECT id FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    if existing is not None:
        return
    now = datetime_to_db(datetime.now(UTC))
    type_value = (
        source_type.value if isinstance(source_type, SourceType) else str(source_type)
    )
    connection.execute(
        """
        INSERT INTO sources (
            id, name, type, status, enabled, configuration_json,
            created_at, updated_at, last_health_check_at, last_error
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL)
        """,
        (
            source_id,
            name or source_id,
            type_value,
            "unknown",
            1,
            now,
            now,
        ),
    )
