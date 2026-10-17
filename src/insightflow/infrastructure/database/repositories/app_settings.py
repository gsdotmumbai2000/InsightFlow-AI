"""SQLite user-adjustable runtime settings repository."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.serialization import datetime_to_db


class SQLiteAppSettingsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, key: str) -> str | None:
        def _op() -> str | None:
            row = self._connection.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
            return None if row is None else str(row["value"])

        return run_db(_op, entity="app_settings")

    def set(self, key: str, value: str) -> None:
        def _op() -> None:
            self._connection.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (:key, :value, :updated_at)
                ON CONFLICT (key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                {
                    "key": key,
                    "value": value,
                    "updated_at": datetime_to_db(datetime.now(UTC)),
                },
            )

        run_db(_op, entity="app_settings")

    def delete(self, key: str) -> None:
        def _op() -> None:
            self._connection.execute("DELETE FROM app_settings WHERE key = ?", (key,))

        run_db(_op, entity="app_settings")
