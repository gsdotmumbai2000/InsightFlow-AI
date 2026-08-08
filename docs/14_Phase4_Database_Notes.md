# InsightFlow AI — Phase 4 database implementation notes

## Database location

`{AppDirectories.database}/insightflow.db`

On Windows this is typically:

`%LOCALAPPDATA%\InsightFlow\database\insightflow.db`

Paths come from Phase 2 configuration; no user-specific path is hardcoded.

## Migration strategy

- SQL files live in repository-root `migrations/` as `NNN_name.sql`.
- Versions are recorded in `schema_migrations(version, name, applied_at)`.
- `initialize_database()` is idempotent and runs on application startup and when a unit of work opens.
- Migration SQL uses `IF NOT EXISTS` because SQLite `executescript` cannot fully wrap DDL in an atomic rollback.

## SQLite settings

| Setting | Value | Why |
|---|---|---|
| foreign_keys | ON | Enforce relational integrity |
| journal_mode | WAL | Safer concurrent readers with a writer |
| busy_timeout | 5000 ms | Reduce lock failures under UI/worker contention |
| synchronous | NORMAL | Reliable with WAL without FULL's extra fsync cost |
| check_same_thread | True | Prevent unsafe cross-thread connection reuse |
| isolation_level | None | Explicit BEGIN/COMMIT in the unit of work |

## Connection / threading

Each `SQLiteUnitOfWork` owns one connection for its lifetime on the calling thread.
Do not share that connection across threads. Create a new unit of work per logical transaction.

## Transactions

```text
with unit_of_work_factory() as uow:
    uow.topics.add(...)
    uow.events.add(...)
    uow.commit()
```

If the context exits with an exception and commit was not called, the unit of work rolls back.

## Repository architecture

Application ports define repository contracts. Infrastructure SQLite repositories map domain entities through explicit mappers. Domain entities never contain SQL.

## Error translation

`sqlite3.IntegrityError` / `OperationalError` are translated to:

- `DuplicateEntityError`
- `PersistenceError`
- `DatabaseUnavailableError`
- `TransactionError`
- `DataMappingError`

## Storage conventions

- Timestamps: ISO-8601 UTC ending in `Z`
- Enums: stable string values
- Structured fields: JSON text with deterministic `sort_keys`
- Booleans: INTEGER 0/1

## Deferred tables

Intentionally not created in Phase 4:

- `monitoring_state` (Gmail watch/history; later phase)
- `processing_attempts` (optional detail; `processing_records` exists)
- `rules`, `rule_executions`
- `content_jobs`, `content_assets`
- `application_settings`
- `source_credentials_metadata`

Roadmap name `processing_jobs` is implemented as `processing_records` per `06_Database_Design.md`.
