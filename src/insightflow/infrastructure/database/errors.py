"""SQLite error translation helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from insightflow.application.exceptions import (
    DuplicateEntityError,
    PersistenceError,
)


def translate_integrity(
    exc: sqlite3.IntegrityError, *, entity: str
) -> PersistenceError:
    message = str(exc).lower()
    if "unique" in message:
        return DuplicateEntityError(f"Duplicate {entity}: {exc}")
    return PersistenceError(f"Integrity error for {entity}: {exc}")


def run_db[T](operation: Callable[[], T], *, entity: str) -> T:
    try:
        return operation()
    except sqlite3.IntegrityError as exc:
        raise translate_integrity(exc, entity=entity) from exc
    except sqlite3.Error as exc:
        raise PersistenceError(f"Database error for {entity}: {exc}") from exc
