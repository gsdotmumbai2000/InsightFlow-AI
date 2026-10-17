-- InsightFlow AI — Custom AI output and AI profile deletion
--
-- Additive only — brand-new tables, idempotent via CREATE TABLE IF NOT
-- EXISTS; no ALTER TABLE (see infrastructure/database/migrations.py).
--
-- ai_analysis_contents: the free text an AI profile with output style
-- CUSTOM_TEXT asked for (e.g. a news script). One row per analysis that has
-- such text; structured analyses have none.
--
-- ai_profile_deletions: profiles the user deleted. The ai_profiles row stays
-- because ai_analyses references it (foreign key) — deleting a profile must
-- not delete the analyses it produced. Deleted profiles are hidden from
-- lists and lookups and unassigned from topics.

CREATE TABLE IF NOT EXISTS ai_analysis_contents (
    analysis_id TEXT NOT NULL PRIMARY KEY,
    generated_content TEXT NOT NULL,
    FOREIGN KEY (analysis_id) REFERENCES ai_analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_profile_deletions (
    ai_profile_id TEXT NOT NULL PRIMARY KEY,
    deleted_at TEXT NOT NULL,
    FOREIGN KEY (ai_profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
);
