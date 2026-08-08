"""Infrastructure database package."""

from __future__ import annotations

from insightflow.infrastructure.database.connection import connect, connection_scope
from insightflow.infrastructure.database.migrations import initialize_database
from insightflow.infrastructure.database.unit_of_work import (
    SQLiteUnitOfWork,
    create_unit_of_work,
)

__all__ = [
    "SQLiteUnitOfWork",
    "connect",
    "connection_scope",
    "create_unit_of_work",
    "initialize_database",
]
