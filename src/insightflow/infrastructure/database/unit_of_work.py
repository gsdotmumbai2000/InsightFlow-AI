"""SQLite unit of work."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

from insightflow.application.exceptions import TransactionError
from insightflow.application.ports.repositories import (
    AIAnalysisRepository,
    AIProfileRepository,
    AttachmentRepository,
    IntelligenceEventRepository,
    NotificationRepository,
    StoryRepository,
    TopicRepository,
    UnitOfWork,
)
from insightflow.infrastructure.database.connection import connect
from insightflow.infrastructure.database.migrations import initialize_database
from insightflow.infrastructure.database.repositories.analyses import (
    SQLiteAIAnalysisRepository,
)
from insightflow.infrastructure.database.repositories.attachments import (
    SQLiteAttachmentRepository,
)
from insightflow.infrastructure.database.repositories.events import (
    SQLiteIntelligenceEventRepository,
)
from insightflow.infrastructure.database.repositories.notifications import (
    SQLiteNotificationRepository,
)
from insightflow.infrastructure.database.repositories.profiles import (
    SQLiteAIProfileRepository,
)
from insightflow.infrastructure.database.repositories.stories import (
    SQLiteStoryRepository,
)
from insightflow.infrastructure.database.repositories.topics import (
    SQLiteTopicRepository,
)


class SQLiteUnitOfWork:
    """One connection + transaction per unit-of-work instance (thread-affine)."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None
        self._committed = False
        self.topics: TopicRepository
        self.events: IntelligenceEventRepository
        self.profiles: AIProfileRepository
        self.analyses: AIAnalysisRepository
        self.attachments: AttachmentRepository
        self.notifications: NotificationRepository
        self.stories: StoryRepository

    def __enter__(self) -> UnitOfWork:
        self._connection = connect(self._database_path)
        initialize_database(self._connection)
        assert self._connection is not None
        self.topics = SQLiteTopicRepository(self._connection)
        self.events = SQLiteIntelligenceEventRepository(self._connection)
        self.profiles = SQLiteAIProfileRepository(self._connection)
        self.analyses = SQLiteAIAnalysisRepository(self._connection)
        self.attachments = SQLiteAttachmentRepository(self._connection)
        self.notifications = SQLiteNotificationRepository(self._connection)
        self.stories = SQLiteStoryRepository(self._connection)
        try:
            self._connection.execute("BEGIN")
        except sqlite3.Error as exc:
            self._connection.close()
            self._connection = None
            raise TransactionError(f"Unable to begin transaction: {exc}") from exc
        self._committed = False
        return cast(UnitOfWork, self)

    def commit(self) -> None:
        if self._connection is None:
            raise TransactionError("Unit of work is not active.")
        try:
            self._connection.execute("COMMIT")
            self._committed = True
        except sqlite3.Error as exc:
            raise TransactionError(f"Commit failed: {exc}") from exc

    def rollback(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.execute("ROLLBACK")
        except sqlite3.Error as exc:
            raise TransactionError(f"Rollback failed: {exc}") from exc
        self._committed = True  # prevent double rollback on exit

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        try:
            if self._connection is not None and not self._committed:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self._connection is not None:
                self._connection.close()
                self._connection = None


def create_unit_of_work(database_path: Path) -> UnitOfWork:
    """Factory used by the composition root."""
    return cast(UnitOfWork, SQLiteUnitOfWork(database_path))
