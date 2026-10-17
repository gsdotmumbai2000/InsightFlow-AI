"""SQLite monitoring-control (desired-state) repository (Phase 13)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from insightflow.domain import MonitoringDesiredStatus, SourceType
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.serialization import datetime_to_db


class SQLiteMonitoringControlRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_desired(
        self, *, account_id: str, provider: SourceType
    ) -> MonitoringDesiredStatus:
        def _op() -> MonitoringDesiredStatus:
            row = self._connection.execute(
                """
                SELECT desired_status FROM monitoring_control
                WHERE account_id = ? AND provider = ?
                """,
                (account_id, provider.value),
            ).fetchone()
            if row is None:
                return MonitoringDesiredStatus.STOPPED
            return MonitoringDesiredStatus(row["desired_status"])

        return run_db(_op, entity="monitoring_control")

    def set_desired(
        self,
        *,
        account_id: str,
        provider: SourceType,
        desired: MonitoringDesiredStatus,
    ) -> None:
        def _op() -> None:
            self._connection.execute(
                """
                INSERT INTO monitoring_control (
                    account_id, provider, desired_status, updated_at
                ) VALUES (:account_id, :provider, :desired_status, :updated_at)
                ON CONFLICT (account_id, provider) DO UPDATE SET
                    desired_status = excluded.desired_status,
                    updated_at = excluded.updated_at
                """,
                {
                    "account_id": account_id,
                    "provider": provider.value,
                    "desired_status": desired.value,
                    "updated_at": datetime_to_db(datetime.now(UTC)),
                },
            )

        run_db(_op, entity="monitoring_control")
