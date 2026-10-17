"""SQLite notification repository."""

from __future__ import annotations

import sqlite3

from insightflow.domain import Notification, NotificationId, NotificationStatus
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import (
    notification_from_row,
    notification_to_row,
)


class SQLiteNotificationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, notification: Notification) -> None:
        def _op() -> None:
            row = notification_to_row(notification)
            self._connection.execute(
                """
                INSERT INTO notifications (
                    id, event_id, topic_id, priority, notification_type, title,
                    summary, status, provider, created_at, updated_at,
                    displayed_at, dismissed_at, opened_at, failure_message
                ) VALUES (
                    :id, :event_id, :topic_id, :priority, :notification_type, :title,
                    :summary, :status, :provider, :created_at, :updated_at,
                    :displayed_at, :dismissed_at, NULL, :failure_message
                )
                """,
                row,
            )

        run_db(_op, entity="notification")

    def get(self, notification_id: NotificationId) -> Notification | None:
        def _op() -> Notification | None:
            row = self._connection.execute(
                "SELECT * FROM notifications WHERE id = ?",
                (notification_id.value,),
            ).fetchone()
            return notification_from_row(row) if row else None

        return run_db(_op, entity="notification")

    def update(self, notification: Notification) -> None:
        def _op() -> None:
            row = notification_to_row(notification)
            cursor = self._connection.execute(
                """
                UPDATE notifications SET
                    priority = :priority,
                    notification_type = :notification_type,
                    title = :title,
                    summary = :summary,
                    status = :status,
                    updated_at = :updated_at,
                    displayed_at = :displayed_at,
                    dismissed_at = :dismissed_at,
                    failure_message = :failure_message
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise KeyError(notification.id.value)

        run_db(_op, entity="notification")

    def list_pending(self) -> list[Notification]:
        def _op() -> list[Notification]:
            rows = self._connection.execute(
                """
                SELECT * FROM notifications
                WHERE status = ?
                ORDER BY created_at
                """,
                (NotificationStatus.PENDING.value,),
            ).fetchall()
            return [notification_from_row(row) for row in rows]

        return run_db(_op, entity="notification")

    def list_recent(self, *, limit: int = 100) -> list[Notification]:
        def _op() -> list[Notification]:
            rows = self._connection.execute(
                """
                SELECT * FROM notifications
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [notification_from_row(row) for row in rows]

        return run_db(_op, entity="notification")

    def delete_all(self) -> int:
        def _op() -> int:
            return self._connection.execute("DELETE FROM notifications").rowcount

        return run_db(_op, entity="notification")
