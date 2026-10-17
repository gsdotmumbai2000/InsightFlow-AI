-- InsightFlow AI — Gmail real-time monitoring state (Phase 10)
-- Source of truth: docs/17_Phase10_Gmail_Realtime_Monitoring_Notes.md
--
-- Deferred from migration 001 per docs/14_Phase4_Database_Notes.md
-- ("monitoring_state deferred to Gmail monitoring phase").
--
-- Never stores: OAuth tokens, Pub/Sub credentials, email body/content.
-- Identity: one row per (account_id, provider) pair — designed so a future
-- multi-account architecture only needs additional rows, not a schema change.

CREATE TABLE IF NOT EXISTS monitoring_state (
    id TEXT NOT NULL PRIMARY KEY,
    account_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    pubsub_project_id TEXT,
    pubsub_topic TEXT,
    pubsub_subscription TEXT,
    current_history_id TEXT,
    watch_expiration TEXT,
    status TEXT NOT NULL,
    last_notification_at TEXT,
    last_sync_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (account_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_state_status ON monitoring_state(status);
