-- InsightFlow AI — User-adjustable runtime settings
--
-- Additive only — a brand-new table, idempotent via CREATE TABLE IF NOT
-- EXISTS (see infrastructure/database/migrations.py:apply_migrations).
--
-- Holds settings the user changes in the Desktop Settings page that the
-- Background Agent must pick up without a restart (e.g. the AI output token
-- limit). The database is the coordination point between the two processes,
-- as for monitoring_control (003). A missing key means "use the value from
-- configuration (.env)".
--
-- Never stores: OAuth tokens, credentials, API keys, email content.

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
