"""SQLite story repository."""

from __future__ import annotations

import sqlite3

from insightflow.domain import EventId, Story, StoryId, TopicId
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import story_from_row, story_to_row
from insightflow.infrastructure.database.serialization import datetime_to_db


class SQLiteStoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, story: Story) -> None:
        def _op() -> None:
            row = story_to_row(story)
            self._connection.execute(
                """
                INSERT INTO stories (
                    id, topic_id, title, summary, status,
                    first_event_at, last_event_at, created_at, updated_at
                ) VALUES (
                    :id, :topic_id, :title, :summary, :status,
                    :first_event_at, :last_event_at, :created_at, :updated_at
                )
                """,
                row,
            )
            self._replace_story_events(story)

        run_db(_op, entity="story")

    def get(self, story_id: StoryId) -> Story | None:
        def _op() -> Story | None:
            row = self._connection.execute(
                "SELECT * FROM stories WHERE id = ?", (story_id.value,)
            ).fetchone()
            if row is None:
                return None
            return story_from_row(row, self._event_ids(story_id.value))

        return run_db(_op, entity="story")

    def update(self, story: Story) -> None:
        def _op() -> None:
            row = story_to_row(story)
            cursor = self._connection.execute(
                """
                UPDATE stories SET
                    topic_id = :topic_id,
                    title = :title,
                    summary = :summary,
                    status = :status,
                    first_event_at = :first_event_at,
                    last_event_at = :last_event_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise KeyError(story.id.value)
            self._replace_story_events(story)

        run_db(_op, entity="story")

    def list_by_topic(self, topic_id: TopicId) -> list[Story]:
        def _op() -> list[Story]:
            rows = self._connection.execute(
                """
                SELECT * FROM stories
                WHERE topic_id = ?
                ORDER BY COALESCE(last_event_at, created_at) DESC
                """,
                (topic_id.value,),
            ).fetchall()
            return [story_from_row(row, self._event_ids(row["id"])) for row in rows]

        return run_db(_op, entity="story")

    def _event_ids(self, story_id: str) -> tuple[EventId, ...]:
        rows = self._connection.execute(
            """
            SELECT event_id FROM story_events
            WHERE story_id = ?
            ORDER BY added_at
            """,
            (story_id,),
        ).fetchall()
        return tuple(EventId(row["event_id"]) for row in rows)

    def _replace_story_events(self, story: Story) -> None:
        self._connection.execute(
            "DELETE FROM story_events WHERE story_id = ?", (story.id.value,)
        )
        added_at = datetime_to_db(story.updated_at)
        for event_id in story.event_ids:
            self._connection.execute(
                """
                INSERT INTO story_events (story_id, event_id, relevance_score, added_at)
                VALUES (?, ?, NULL, ?)
                """,
                (story.id.value, event_id.value, added_at),
            )
