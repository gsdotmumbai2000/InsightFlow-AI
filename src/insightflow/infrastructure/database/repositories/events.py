"""SQLite intelligence event repository."""

from __future__ import annotations

import sqlite3

from insightflow.domain import EventId, IntelligenceEvent, TopicId
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import event_from_row, event_to_row
from insightflow.infrastructure.database.sources import ensure_source


class SQLiteIntelligenceEventRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, event: IntelligenceEvent) -> None:
        def _op() -> None:
            ensure_source(
                self._connection,
                source_id=event.source.source_id,
                source_type=event.source.source_type,
            )
            row = event_to_row(event)
            self._connection.execute(
                """
                INSERT INTO intelligence_events (
                    id, source_id, topic_id, external_id, external_thread_id,
                    occurred_at, received_at, title, author, content_text,
                    content_hash, source_url, source_type, account_id,
                    metadata_json, raw_metadata_json, status, priority, story_id,
                    created_at, updated_at
                ) VALUES (
                    :id, :source_id, :topic_id, :external_id, :external_thread_id,
                    :occurred_at, :received_at, :title, :author, :content_text,
                    :content_hash, :source_url, :source_type, :account_id,
                    :metadata_json, NULL, :status, :priority, :story_id,
                    :created_at, :updated_at
                )
                """,
                row,
            )

        run_db(_op, entity="intelligence_event")

    def get(self, event_id: EventId) -> IntelligenceEvent | None:
        def _op() -> IntelligenceEvent | None:
            row = self._connection.execute(
                "SELECT * FROM intelligence_events WHERE id = ?",
                (event_id.value,),
            ).fetchone()
            return event_from_row(row) if row else None

        return run_db(_op, entity="intelligence_event")

    def update(self, event: IntelligenceEvent) -> None:
        def _op() -> None:
            row = event_to_row(event)
            cursor = self._connection.execute(
                """
                UPDATE intelligence_events SET
                    topic_id = :topic_id,
                    external_thread_id = :external_thread_id,
                    occurred_at = :occurred_at,
                    received_at = :received_at,
                    title = :title,
                    content_text = :content_text,
                    content_hash = :content_hash,
                    source_url = :source_url,
                    source_type = :source_type,
                    account_id = :account_id,
                    metadata_json = :metadata_json,
                    status = :status,
                    priority = :priority,
                    story_id = :story_id,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise KeyError(event.id.value)

        run_db(_op, entity="intelligence_event")

    def find_by_external_id(
        self, *, source_id: str, external_id: str
    ) -> IntelligenceEvent | None:
        def _op() -> IntelligenceEvent | None:
            row = self._connection.execute(
                """
                SELECT * FROM intelligence_events
                WHERE source_id = ? AND external_id = ?
                """,
                (source_id, external_id),
            ).fetchone()
            return event_from_row(row) if row else None

        return run_db(_op, entity="intelligence_event")

    def list_by_topic(
        self, topic_id: TopicId, *, limit: int = 100
    ) -> list[IntelligenceEvent]:
        def _op() -> list[IntelligenceEvent]:
            rows = self._connection.execute(
                """
                SELECT * FROM intelligence_events
                WHERE topic_id = ?
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (topic_id.value, limit),
            ).fetchall()
            return [event_from_row(row) for row in rows]

        return run_db(_op, entity="intelligence_event")

    def list_recent(self, *, limit: int = 100) -> list[IntelligenceEvent]:
        def _op() -> list[IntelligenceEvent]:
            rows = self._connection.execute(
                """
                SELECT * FROM intelligence_events
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [event_from_row(row) for row in rows]

        return run_db(_op, entity="intelligence_event")
