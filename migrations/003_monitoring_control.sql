-- InsightFlow AI — Monitoring desired-state coordination (Phase 13)
-- Source of truth: docs/ Phase 13 Background Agent notes.
--
-- Additive only — a brand-new table, never touching monitoring_state (001/002),
-- so this migration stays idempotent via CREATE TABLE IF NOT EXISTS even if
-- retried after a crash between DDL and schema_migrations bookkeeping (see
-- infrastructure/database/migrations.py:apply_migrations).
--
-- Distinguishes *desired* monitoring state (what the user asked for, written
-- by the Desktop UI) from *actual* monitoring state (monitoring_state.status,
-- owned by the Background Agent). The Agent's MonitoringDesiredStateReconciler
-- polls this table and starts/stops the real worker to match it — this is
-- the entire "database as coordination point" mechanism; no IPC, no port.
--
-- Never stores: OAuth tokens, Pub/Sub credentials, email body/content.

CREATE TABLE IF NOT EXISTS monitoring_control (
    account_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    desired_status TEXT NOT NULL DEFAULT 'STOPPED',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (account_id, provider)
);
