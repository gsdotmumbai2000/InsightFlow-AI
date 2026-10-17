"""SQLite monitoring-state repository (Phase 10)."""

from __future__ import annotations

import sqlite3

from insightflow.application.exceptions import PersistenceError
from insightflow.domain import MonitoringState, MonitoringStateId, SourceType
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import (
    monitoring_state_from_row,
    monitoring_state_to_row,
)


class SQLiteMonitoringStateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, state: MonitoringState) -> None:
        def _op() -> None:
            row = monitoring_state_to_row(state)
            self._connection.execute(
                """
                INSERT INTO monitoring_state (
                    id, account_id, provider, pubsub_project_id, pubsub_topic,
                    pubsub_subscription, current_history_id, watch_expiration,
                    status, last_notification_at, last_sync_at, last_error,
                    created_at, updated_at
                ) VALUES (
                    :id, :account_id, :provider, :pubsub_project_id, :pubsub_topic,
                    :pubsub_subscription, :current_history_id, :watch_expiration,
                    :status, :last_notification_at, :last_sync_at, :last_error,
                    :created_at, :updated_at
                )
                """,
                row,
            )

        run_db(_op, entity="monitoring_state")

    def get(self, state_id: MonitoringStateId) -> MonitoringState | None:
        def _op() -> MonitoringState | None:
            row = self._connection.execute(
                "SELECT * FROM monitoring_state WHERE id = ?", (state_id.value,)
            ).fetchone()
            return monitoring_state_from_row(row) if row else None

        return run_db(_op, entity="monitoring_state")

    def get_by_account(
        self, *, account_id: str, provider: SourceType
    ) -> MonitoringState | None:
        def _op() -> MonitoringState | None:
            row = self._connection.execute(
                """
                SELECT * FROM monitoring_state
                WHERE account_id = ? AND provider = ?
                """,
                (account_id, provider.value),
            ).fetchone()
            return monitoring_state_from_row(row) if row else None

        return run_db(_op, entity="monitoring_state")

    def update(self, state: MonitoringState) -> None:
        def _op() -> None:
            row = monitoring_state_to_row(state)
            cursor = self._connection.execute(
                """
                UPDATE monitoring_state SET
                    pubsub_project_id = :pubsub_project_id,
                    pubsub_topic = :pubsub_topic,
                    pubsub_subscription = :pubsub_subscription,
                    current_history_id = :current_history_id,
                    watch_expiration = :watch_expiration,
                    status = :status,
                    last_notification_at = :last_notification_at,
                    last_sync_at = :last_sync_at,
                    last_error = :last_error,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise PersistenceError(f"Monitoring state not found: {state.id.value}")

        run_db(_op, entity="monitoring_state")
