-- InsightFlow AI initial schema (schema version 1)
-- Source of truth: docs/06_Database_Design.md
-- Phase 4 notes:
--   * topics.status added to preserve ENABLED/DISABLED/PAUSED from the domain
--   * processing_records implements the roadmap "processing_jobs" concept
--   * monitoring_state deferred to Gmail monitoring phase
--   * rules, rule_executions, content_jobs, application_settings deferred

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    configuration_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_health_check_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS ai_profiles (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    active_version_id TEXT,
    enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_profile_versions (
    id TEXT NOT NULL PRIMARY KEY,
    ai_profile_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    output_schema_json TEXT NOT NULL,
    model_preferences_json TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT,
    is_active INTEGER NOT NULL,
    FOREIGN KEY (ai_profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE,
    UNIQUE (ai_profile_id, version_number)
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    source_id TEXT NOT NULL,
    source_identifier TEXT NOT NULL,
    source_type TEXT NOT NULL,
    ai_profile_id TEXT,
    priority_policy_json TEXT,
    notification_policy_json TEXT,
    attachment_policy_json TEXT,
    content_policy_json TEXT,
    status TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (ai_profile_id) REFERENCES ai_profiles(id),
    UNIQUE (source_id, source_identifier)
);

CREATE TABLE IF NOT EXISTS stories (
    id TEXT NOT NULL PRIMARY KEY,
    topic_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    status TEXT NOT NULL,
    first_event_at TEXT,
    last_event_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS intelligence_events (
    id TEXT NOT NULL PRIMARY KEY,
    source_id TEXT NOT NULL,
    topic_id TEXT,
    external_id TEXT NOT NULL,
    external_thread_id TEXT,
    occurred_at TEXT,
    received_at TEXT NOT NULL,
    title TEXT,
    author TEXT,
    content_text TEXT,
    content_hash TEXT,
    source_url TEXT,
    source_type TEXT NOT NULL,
    account_id TEXT,
    metadata_json TEXT,
    raw_metadata_json TEXT,
    status TEXT NOT NULL,
    priority TEXT,
    story_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (story_id) REFERENCES stories(id),
    UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS story_events (
    story_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    relevance_score REAL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (story_id, event_id),
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES intelligence_events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS processing_records (
    id TEXT NOT NULL PRIMARY KEY,
    event_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL,
    correlation_id TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    next_retry_at TEXT,
    last_error_type TEXT,
    last_error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES intelligence_events(id) ON DELETE CASCADE,
    UNIQUE (event_id)
);

CREATE TABLE IF NOT EXISTS ai_analyses (
    id TEXT NOT NULL PRIMARY KEY,
    event_id TEXT NOT NULL,
    ai_profile_id TEXT NOT NULL,
    ai_profile_version_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    headline TEXT,
    summary TEXT NOT NULL,
    why_it_matters TEXT,
    facts_json TEXT,
    what_to_watch_json TEXT,
    entities_json TEXT,
    importance TEXT,
    priority TEXT,
    confidence REAL,
    sentiment TEXT,
    uncertainty_json TEXT,
    topic_analysis_json TEXT,
    market_impact_json TEXT,
    follow_up_json TEXT,
    status TEXT NOT NULL,
    failure_reason TEXT,
    raw_response_reference TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES intelligence_events(id) ON DELETE CASCADE,
    FOREIGN KEY (ai_profile_id) REFERENCES ai_profiles(id),
    FOREIGN KEY (ai_profile_version_id) REFERENCES ai_profile_versions(id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT NOT NULL PRIMARY KEY,
    event_id TEXT NOT NULL,
    external_id TEXT,
    filename TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER,
    download_status TEXT NOT NULL,
    processing_status TEXT NOT NULL,
    storage_reference TEXT,
    content_hash TEXT,
    extracted_text TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES intelligence_events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT NOT NULL PRIMARY KEY,
    event_id TEXT NOT NULL,
    topic_id TEXT,
    priority TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    displayed_at TEXT,
    dismissed_at TEXT,
    opened_at TEXT,
    failure_message TEXT,
    FOREIGN KEY (event_id) REFERENCES intelligence_events(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS audit_records (
    id TEXT NOT NULL PRIMARY KEY,
    action TEXT NOT NULL,
    actor TEXT,
    entity_type TEXT,
    entity_id TEXT,
    correlation_id TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_topics_enabled ON topics(enabled);
CREATE INDEX IF NOT EXISTS idx_topics_source ON topics(source_id, source_identifier);
CREATE INDEX IF NOT EXISTS idx_events_source_external ON intelligence_events(source_id, external_id);
CREATE INDEX IF NOT EXISTS idx_events_topic_occurred ON intelligence_events(topic_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_received_at ON intelligence_events(received_at);
CREATE INDEX IF NOT EXISTS idx_events_content_hash ON intelligence_events(content_hash);
CREATE INDEX IF NOT EXISTS idx_events_status ON intelligence_events(status);
CREATE INDEX IF NOT EXISTS idx_events_priority ON intelligence_events(priority);
CREATE INDEX IF NOT EXISTS idx_processing_status_retry ON processing_records(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_analyses_event ON ai_analyses(event_id);
CREATE INDEX IF NOT EXISTS idx_analyses_profile_created ON ai_analyses(ai_profile_id, created_at);
CREATE INDEX IF NOT EXISTS idx_attachments_event ON attachments(event_id);
CREATE INDEX IF NOT EXISTS idx_attachments_download ON attachments(download_status);
CREATE INDEX IF NOT EXISTS idx_notifications_status_created ON notifications(status, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_topic_created ON notifications(topic_id, created_at);
CREATE INDEX IF NOT EXISTS idx_stories_topic_last ON stories(topic_id, last_event_at);
CREATE INDEX IF NOT EXISTS idx_story_events_event ON story_events(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity_created ON audit_records(entity_type, entity_id, created_at);
