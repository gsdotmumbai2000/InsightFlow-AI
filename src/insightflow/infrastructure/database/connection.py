"""SQLite connection management for InsightFlow AI.

Connection ownership
--------------------
Each :class:`~insightflow.infrastructure.database.unit_of_work.SQLiteUnitOfWork`
owns one ``sqlite3.Connection`` for its lifetime. Connections are **not** shared
across threads (``check_same_thread=True``). Create a new unit of work per
logical transaction on the calling thread.

SQLite settings
---------------
- ``foreign_keys=ON`` — enforce relational integrity.
- ``journal_mode=WAL`` — better concurrent readers while a writer is active.
- ``busy_timeout=5000`` — wait briefly for locks instead of failing immediately.
- ``synchronous=NORMAL`` — durable enough for a desktop app with WAL; avoids
  FULL's extra fsync cost without using OFF.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from insightflow.application.exceptions import (
    DatabaseUnavailableError,
    PersistenceError,
)

DEFAULT_BUSY_TIMEOUT_MS = 5_000


def connect(
    database_path: Path, *, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open a configured SQLite connection for ``database_path``."""
    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            database_path,
            timeout=busy_timeout_ms / 1000,
            isolation_level=None,  # manual transaction control
            check_same_thread=True,
        )
    except sqlite3.Error as exc:
        raise DatabaseUnavailableError(
            f"Unable to open SQLite database at {database_path}: {exc}"
        ) from exc

    connection.row_factory = sqlite3.Row
    _configure_connection(connection, busy_timeout_ms=busy_timeout_ms)
    return connection


def _configure_connection(
    connection: sqlite3.Connection, *, busy_timeout_ms: int
) -> None:
    try:
        connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.Error as exc:
        connection.close()
        raise DatabaseUnavailableError(
            f"Unable to configure SQLite connection: {exc}"
        ) from exc


@contextmanager
def connection_scope(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a configured connection and always close it."""
    connection = connect(database_path)
    try:
        yield connection
    finally:
        try:
            connection.close()
        except sqlite3.Error as exc:
            raise PersistenceError(f"Failed to close SQLite connection: {exc}") from exc
