-- InsightFlow AI — Remember messages the user cleared
--
-- Additive only — a brand-new table, idempotent via CREATE TABLE IF NOT
-- EXISTS; no ALTER TABLE (see infrastructure/database/migrations.py).
--
-- "Clear all" on the Intelligence page deletes every intelligence event
-- (analyses, notifications, and attachments cascade). Gmail full sync
-- re-reads recent messages on every Agent start and skips only messages it
-- already has, so without this record every cleared message would be
-- re-ingested — with new toasts and new AI calls. Ingestion treats a source
-- identity listed here like an existing event.
--
-- Stores only message identifiers, never content.

CREATE TABLE IF NOT EXISTS cleared_event_sources (
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    cleared_at TEXT NOT NULL,
    PRIMARY KEY (source_id, external_id)
);
