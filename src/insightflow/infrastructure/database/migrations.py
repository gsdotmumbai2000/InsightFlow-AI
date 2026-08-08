"""Ordered SQLite schema migrations."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from insightflow.application.exceptions import PersistenceError, TransactionError

_PACKAGE_ROOT = Path(__file__).resolve().parents[4]
_CANDIDATE_DIRS = (
    _PACKAGE_ROOT / "migrations",
    Path.cwd() / "migrations",
)


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    path: Path


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_migrations_dir() -> Path:
    for candidate in _CANDIDATE_DIRS:
        if candidate.is_dir():
            return candidate
    raise PersistenceError(
        "Migrations directory not found. Expected ./migrations relative to the "
        "project root."
    )


def discover_migrations(migrations_dir: Path | None = None) -> list[Migration]:
    directory = migrations_dir or resolve_migrations_dir()
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        stem = path.stem
        if "_" not in stem:
            raise PersistenceError(
                f"Invalid migration filename {path.name}; expected 'NNN_name.sql'."
            )
        version_part, name = stem.split("_", 1)
        try:
            version = int(version_part)
        except ValueError as exc:
            raise PersistenceError(
                f"Invalid migration version in {path.name}."
            ) from exc
        migrations.append(Migration(version=version, name=name, path=path))
    return sorted(migrations, key=lambda item: item.version)


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def applied_versions(connection: sqlite3.Connection) -> set[int]:
    _ensure_migrations_table(connection)
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(row[0]) for row in rows}


def apply_migrations(
    connection: sqlite3.Connection,
    *,
    migrations_dir: Path | None = None,
) -> list[int]:
    """Apply pending migrations. Safe to call repeatedly.

    SQLite ``executescript`` issues an implicit COMMIT before running DDL.
    Migration SQL therefore uses ``IF NOT EXISTS`` so a retry after a crash
    between DDL and version recording remains safe.
    """
    migrations = discover_migrations(migrations_dir)
    already = applied_versions(connection)
    applied: list[int] = []

    for migration in migrations:
        if migration.version in already:
            continue
        sql = migration.path.read_text(encoding="utf-8")
        try:
            connection.executescript(sql)
            connection.execute(
                """
                INSERT INTO schema_migrations (version, name, applied_at)
                VALUES (?, ?, ?)
                """,
                (migration.version, migration.name, _utc_now_iso()),
            )
        except sqlite3.Error as exc:
            raise TransactionError(
                f"Migration {migration.version}_{migration.name} failed: {exc}"
            ) from exc
        applied.append(migration.version)
        already.add(migration.version)
    return applied


def initialize_database(
    connection: sqlite3.Connection,
    *,
    migrations_dir: Path | None = None,
) -> list[int]:
    """Migrate an open connection to the latest schema."""
    return apply_migrations(connection, migrations_dir=migrations_dir)
