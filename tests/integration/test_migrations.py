"""Database migration and initialization tests."""

from __future__ import annotations

from pathlib import Path

from insightflow.infrastructure.database.connection import connect
from insightflow.infrastructure.database.migrations import (
    applied_versions,
    discover_migrations,
    initialize_database,
)


def test_migrations_apply_to_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    connection = connect(db_path)
    try:
        applied = initialize_database(connection)
        assert 1 in applied
        versions = applied_versions(connection)
        assert 1 in versions
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "topics" in tables
        assert "intelligence_events" in tables
        assert "ai_profiles" in tables
        assert "ai_analyses" in tables
        assert "attachments" in tables
        assert "notifications" in tables
        assert "stories" in tables
        assert "processing_records" in tables
        assert "audit_records" in tables
        assert "schema_migrations" in tables
    finally:
        connection.close()


def test_migrations_are_not_applied_twice(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    connection = connect(db_path)
    try:
        first = initialize_database(connection)
        second = initialize_database(connection)
        assert first == [1]
        assert second == []
        assert applied_versions(connection) == {1}
    finally:
        connection.close()


def test_foreign_keys_and_wal_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    connection = connect(db_path)
    try:
        initialize_database(connection)
        fk = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        journal = connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert int(fk) == 1
        assert str(journal).lower() == "wal"
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_events_source_external" in indexes
        assert "idx_events_status" in indexes
        assert "idx_notifications_status_created" in indexes
    finally:
        connection.close()


def test_discover_migrations_finds_initial() -> None:
    migrations = discover_migrations()
    assert migrations
    assert migrations[0].version == 1
