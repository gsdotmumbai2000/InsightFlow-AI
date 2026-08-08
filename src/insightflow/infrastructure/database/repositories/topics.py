"""SQLite topic repository."""

from __future__ import annotations

import sqlite3

from insightflow.application.exceptions import PersistenceError
from insightflow.domain import Topic, TopicId, TopicStatus
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import topic_from_row, topic_to_row
from insightflow.infrastructure.database.sources import ensure_source


class SQLiteTopicRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, topic: Topic) -> None:
        def _op() -> None:
            ensure_source(
                self._connection,
                source_id=topic.source_configuration.source_id,
                source_type=topic.source_configuration.source_type,
            )
            if topic.ai_profile_id is not None:
                self._assert_profile_exists(topic.ai_profile_id.value)
            row = topic_to_row(topic)
            self._connection.execute(
                """
                INSERT INTO topics (
                    id, name, description, source_id, source_identifier, source_type,
                    ai_profile_id, priority_policy_json, notification_policy_json,
                    attachment_policy_json, content_policy_json, status, enabled,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :source_id,
                    :source_identifier, :source_type,
                    :ai_profile_id, NULL, :notification_policy_json,
                    NULL, NULL, :status, :enabled, :created_at, :updated_at
                )
                """,
                row,
            )

        run_db(_op, entity="topic")

    def get(self, topic_id: TopicId) -> Topic | None:
        def _op() -> Topic | None:
            row = self._connection.execute(
                "SELECT * FROM topics WHERE id = ?", (topic_id.value,)
            ).fetchone()
            return topic_from_row(row) if row else None

        return run_db(_op, entity="topic")

    def update(self, topic: Topic) -> None:
        def _op() -> None:
            ensure_source(
                self._connection,
                source_id=topic.source_configuration.source_id,
                source_type=topic.source_configuration.source_type,
            )
            row = topic_to_row(topic)
            cursor = self._connection.execute(
                """
                UPDATE topics SET
                    name = :name,
                    description = :description,
                    source_id = :source_id,
                    source_identifier = :source_identifier,
                    source_type = :source_type,
                    ai_profile_id = :ai_profile_id,
                    notification_policy_json = :notification_policy_json,
                    status = :status,
                    enabled = :enabled,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise PersistenceError(f"Topic not found: {topic.id.value}")

        run_db(_op, entity="topic")

    def list_all(self) -> list[Topic]:
        def _op() -> list[Topic]:
            rows = self._connection.execute(
                "SELECT * FROM topics ORDER BY name COLLATE NOCASE"
            ).fetchall()
            return [topic_from_row(row) for row in rows]

        return run_db(_op, entity="topic")

    def list_enabled(self) -> list[Topic]:
        def _op() -> list[Topic]:
            rows = self._connection.execute(
                """
                SELECT * FROM topics
                WHERE status = ?
                ORDER BY name COLLATE NOCASE
                """,
                (TopicStatus.ENABLED.value,),
            ).fetchall()
            return [topic_from_row(row) for row in rows]

        return run_db(_op, entity="topic")

    def find_by_source_identifier(
        self, *, source_id: str, source_identifier: str
    ) -> Topic | None:
        def _op() -> Topic | None:
            row = self._connection.execute(
                """
                SELECT * FROM topics
                WHERE source_id = ? AND source_identifier = ?
                """,
                (source_id, source_identifier),
            ).fetchone()
            return topic_from_row(row) if row else None

        return run_db(_op, entity="topic")

    def delete(self, topic_id: TopicId) -> None:
        def _op() -> None:
            self._connection.execute(
                "DELETE FROM topics WHERE id = ?", (topic_id.value,)
            )

        run_db(_op, entity="topic")

    def _assert_profile_exists(self, profile_id: str) -> None:
        row = self._connection.execute(
            "SELECT id FROM ai_profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError(
                f"FOREIGN KEY constraint failed: ai_profile_id={profile_id}"
            )
