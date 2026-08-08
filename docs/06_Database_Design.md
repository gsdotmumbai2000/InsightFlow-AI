# InsightFlow AI — Database Design

**Document:** `06_Database_Design.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent:** `05_System_Design.md`

---

# 1. Purpose

This document defines the initial database design for InsightFlow AI.

The database must support:

- Gmail/source configuration.
- Topics and monitored labels.
- AI profiles and prompt versions.
- Incoming intelligence events.
- Processing state and retry/recovery.
- AI summaries and analysis.
- Notifications.
- Attachments.
- Stories and timelines.
- Rules and workflows.
- Future content-generation jobs.
- Audit records.
- Application settings.
- Retention and cleanup.

The initial implementation is designed for a **single-user Windows desktop application** and will use:

```text
SQLite
```

The design must remain sufficiently database-agnostic to permit future migration to PostgreSQL if InsightFlow evolves into a cloud or multi-user platform.

---

# 2. Database Principles

The database design follows these principles:

1. Use stable primary keys.
2. Preserve external provider identifiers.
3. Enforce uniqueness where duplicates are unacceptable.
4. Use foreign keys for relationships.
5. Use indexes for common access patterns.
6. Keep provider-specific data isolated.
7. Store large content carefully.
8. Keep processing state explicit.
9. Preserve auditability.
10. Avoid storing secrets in ordinary tables.
11. Support schema migrations.
12. Support recovery after application restart.
13. Prefer normalized relational structures for core entities.
14. Use JSON only where flexible provider/configuration data genuinely requires it.

---

# 3. Database Technology

## 3.1 Initial Database

```text
SQLite
```

Recommended characteristics:

```text
Single local database file
WAL mode where appropriate
Foreign keys enabled
Versioned migrations
Transactions
Indexed queries
```

---

# 4. Database File

Conceptual location:

```text
%LOCALAPPDATA%\InsightFlow\database\insightflow.db
```

The exact production path will be finalized in deployment documentation.

The application must not hardcode a user-specific path.

---

# 5. Database Schema Version

The database shall maintain a schema version.

Example:

```text
schema_version = 1
```

Database migrations must increment the version.

---

# 6. Entity Relationship Overview

Core relationships:

```text
Source
  |
  +----< Topic
  |
  +----< IntelligenceEvent
                 |
                 +----< ProcessingRecord
                 |
                 +----< AIAnalysis
                 |
                 +----< Attachment
                 |
                 +----< Notification
                 |
                 +----> Story
                 |
                 +----< ContentJob

AIProfile
  |
  +----< AIAnalysis

Topic
  |
  +----< IntelligenceEvent
  |
  +----< Notification
  |
  +----< Rule

Rule
  |
  +----< RuleExecution

Settings
AuditRecord
```

---

# 7. Core Tables

Initial core tables:

```text
sources
topics
ai_profiles
ai_profile_versions
intelligence_events
processing_records
processing_attempts
ai_analyses
attachments
notifications
stories
story_events
rules
rule_executions
content_jobs
audit_records
application_settings
```

Optional/future:

```text
source_credentials_metadata
event_entities
event_tags
search_index
notification_actions
content_assets
```

---

# 8. ID Strategy

The application should use UUIDs for internal identifiers.

Example:

```text
event_id
topic_id
source_id
analysis_id
```

SQLite can store UUIDs as:

```text
TEXT
```

using a canonical string representation.

Example:

```text
550e8400-e29b-41d4-a716-446655440000
```

---

# 9. External IDs

External provider identifiers must be stored separately from internal IDs.

Example:

```text
Internal Event ID:
7e3...

External Gmail Message ID:
18f...

External Gmail Thread ID:
18g...
```

The application must never use an external provider ID as its universal primary key.

---

# 10. Timestamp Strategy

Store timestamps in UTC.

Recommended representation:

```text
ISO-8601 UTC
```

Example:

```text
2026-08-08T09:30:00Z
```

The UI converts timestamps to the user's local timezone.

---

# 11. `sources` Table

Purpose:

Stores external information source definitions.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | Internal UUID |
| name | TEXT | NO | Display name |
| type | TEXT | NO | Source type |
| status | TEXT | NO | Current connection state |
| enabled | INTEGER | NO | 0/1 |
| configuration_json | TEXT | YES | Non-secret configuration |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |
| last_health_check_at | TEXT | YES | UTC |
| last_error | TEXT | YES | Last known error |

Example:

```text
id: ...
name: My Gmail
type: gmail
status: connected
enabled: 1
```

---

# 12. `topics` Table

Purpose:

Stores user-defined monitoring topics.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| name | TEXT | NO | Topic name |
| description | TEXT | YES | Description |
| source_id | TEXT | NO | FK to sources |
| source_identifier | TEXT | NO | Gmail label or source-specific identifier |
| ai_profile_id | TEXT | YES | FK to ai_profiles |
| priority_policy_json | TEXT | YES | Priority configuration |
| notification_policy_json | TEXT | YES | Notification configuration |
| attachment_policy_json | TEXT | YES | Attachment configuration |
| content_policy_json | TEXT | YES | Future content settings |
| enabled | INTEGER | NO | 0/1 |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

Constraint:

```text
UNIQUE(source_id, source_identifier)
```

This prevents the same source label from being configured twice accidentally.

---

# 13. `ai_profiles` Table

Purpose:

Stores logical AI analysis profiles.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| name | TEXT | NO | Profile name |
| description | TEXT | YES | Description |
| active_version_id | TEXT | YES | Current version |
| enabled | INTEGER | NO | 0/1 |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

Examples:

```text
Trading / Geopolitics
Entertainment
Technology
General News
```

---

# 14. `ai_profile_versions` Table

Purpose:

Stores versioned AI instructions.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| ai_profile_id | TEXT | NO | FK |
| version_number | INTEGER | NO | Sequential version |
| system_prompt | TEXT | NO | System instructions |
| output_schema_json | TEXT | NO | Expected output schema |
| model_preferences_json | TEXT | YES | Provider/model preferences |
| created_at | TEXT | NO | UTC |
| created_by | TEXT | YES | User/system |
| is_active | INTEGER | NO | 0/1 |

Constraint:

```text
UNIQUE(ai_profile_id, version_number)
```

---

# 15. Why Prompt Versions Must Be Stored

AI output can change when prompts change.

Therefore every AI analysis should identify:

```text
AI Profile
AI Profile Version
AI Provider
AI Model
```

This makes historical analysis explainable.

---

# 16. `intelligence_events` Table

This is the central table.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | Internal UUID |
| source_id | TEXT | NO | FK |
| topic_id | TEXT | YES | FK |
| external_id | TEXT | NO | Provider event/message ID |
| external_thread_id | TEXT | YES | Provider thread ID |
| occurred_at | TEXT | YES | Source event time |
| received_at | TEXT | NO | Application receipt time |
| title | TEXT | YES | Subject/title |
| author | TEXT | YES | Sender/author |
| content_text | TEXT | YES | Normalized text |
| content_hash | TEXT | YES | SHA-256 |
| source_url | TEXT | YES | Original source |
| metadata_json | TEXT | YES | Provider-neutral metadata |
| raw_metadata_json | TEXT | YES | Optional raw metadata |
| status | TEXT | NO | Current processing status |
| priority | TEXT | YES | Current priority |
| story_id | TEXT | YES | FK |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

---

# 17. Event Uniqueness

At minimum:

```text
UNIQUE(source_id, external_id)
```

This is the primary idempotency protection.

---

# 18. Content Hash

`content_hash` should be generated from normalized content.

Recommended:

```text
SHA-256
```

The hash may be combined with title/source information for stronger duplicate detection.

---

# 19. Event Status

Possible values:

```text
RECEIVED
VALIDATING
NORMALIZED
TOPIC_RESOLVED
DEDUPLICATING
AI_PENDING
AI_PROCESSING
AI_COMPLETED
PERSISTING
NOTIFICATION_PENDING
COMPLETED
RETRY_PENDING
FAILED
DUPLICATE
IGNORED
```

The database should enforce valid values where practical.

---

# 20. `processing_records` Table

Purpose:

Tracks the current lifecycle of an event.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| event_id | TEXT | NO | FK |
| status | TEXT | NO | Current status |
| attempt_count | INTEGER | NO | Number of attempts |
| correlation_id | TEXT | NO | Processing trace |
| started_at | TEXT | YES | UTC |
| completed_at | TEXT | YES | UTC |
| next_retry_at | TEXT | YES | UTC |
| last_error_type | TEXT | YES | Error classification |
| last_error_message | TEXT | YES | Error |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

Constraint:

```text
UNIQUE(event_id)
```

One current processing record per event.

---

# 21. `processing_attempts` Table

Purpose:

Preserves individual processing attempts.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| processing_record_id | TEXT | NO | FK |
| attempt_number | INTEGER | NO | Attempt |
| operation | TEXT | NO | Operation name |
| started_at | TEXT | NO | UTC |
| completed_at | TEXT | YES | UTC |
| status | TEXT | NO | Success/failure |
| error_type | TEXT | YES | Error class |
| error_message | TEXT | YES | Error |
| duration_ms | INTEGER | YES | Duration |
| metadata_json | TEXT | YES | Diagnostics |

This table is useful for troubleshooting and reliability analysis.

---

# 22. `ai_analyses` Table

Purpose:

Stores AI-generated intelligence.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| event_id | TEXT | NO | FK |
| ai_profile_id | TEXT | NO | FK |
| ai_profile_version_id | TEXT | NO | FK |
| provider | TEXT | NO | AI provider |
| model | TEXT | NO | Model |
| headline | TEXT | YES | AI headline |
| summary | TEXT | NO | Main summary |
| facts_json | TEXT | YES | Key facts |
| entities_json | TEXT | YES | Entities |
| importance | TEXT | YES | Importance |
| priority | TEXT | YES | AI priority |
| confidence | REAL | YES | Confidence |
| uncertainty_json | TEXT | YES | Uncertainty |
| topic_analysis_json | TEXT | YES | Topic-specific analysis |
| market_impact_json | TEXT | YES | Trading analysis |
| follow_up_json | TEXT | YES | What to watch |
| raw_response_reference | TEXT | YES | Optional reference |
| input_tokens | INTEGER | YES | Usage |
| output_tokens | INTEGER | YES | Usage |
| latency_ms | INTEGER | YES | AI latency |
| created_at | TEXT | NO | UTC |

---

# 23. AI Analysis Versioning

An event may have multiple AI analyses over time.

Example:

```text
Event
 |
 +-- Analysis using Profile v1
 |
 +-- Analysis using Profile v2
```

Therefore `event_id` should not necessarily be globally unique in `ai_analyses`.

The application should identify which analysis is currently active.

Optional future field:

```text
is_current
```

---

# 24. `attachments` Table

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| event_id | TEXT | NO | FK |
| external_id | TEXT | YES | Gmail attachment ID |
| filename | TEXT | NO | Original filename |
| mime_type | TEXT | YES | MIME |
| size_bytes | INTEGER | YES | Size |
| download_status | TEXT | NO | Download state |
| processing_status | TEXT | NO | Processing state |
| storage_reference | TEXT | YES | Local/cloud reference |
| content_hash | TEXT | YES | SHA-256 |
| extracted_text | TEXT | YES | Optional extracted text |
| metadata_json | TEXT | YES | Metadata |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

---

# 25. Attachment States

Download:

```text
NOT_REQUESTED
PENDING
DOWNLOADING
DOWNLOADED
FAILED
```

Processing:

```text
NOT_REQUESTED
PENDING
PROCESSING
COMPLETED
FAILED
UNSUPPORTED
```

---

# 26. Attachment Storage

The database should not store large binary files directly in the initial design.

Instead:

```text
Database
    |
    +--> storage_reference
              |
              v
        Local File Storage
```

This prevents the SQLite database from becoming unnecessarily large.

---

# 27. Attachment Security Metadata

Store:

```text
Original filename
Sanitized filename
MIME type
Size
Hash
```

where necessary.

The application must never execute downloaded files automatically.

---

# 28. `notifications` Table

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| event_id | TEXT | NO | FK |
| topic_id | TEXT | YES | FK |
| priority | TEXT | NO | Priority |
| title | TEXT | NO | Display title |
| summary | TEXT | YES | Display summary |
| status | TEXT | NO | Notification status |
| provider | TEXT | NO | windows |
| created_at | TEXT | NO | UTC |
| displayed_at | TEXT | YES | UTC |
| dismissed_at | TEXT | YES | UTC |
| opened_at | TEXT | YES | UTC |
| failure_message | TEXT | YES | Error |

---

# 29. Notification Status

```text
PENDING
DISPLAYED
DISMISSED
OPENED
SUPPRESSED
FAILED
```

---

# 30. Notification Deduplication

The system should avoid creating repeated notifications for the same event unless explicitly configured.

A future notification policy may allow:

```text
Notify again if priority increases
Notify again if story changes significantly
```

---

# 31. `stories` Table

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| topic_id | TEXT | YES | FK |
| title | TEXT | NO | Story title |
| summary | TEXT | YES | Current AI summary |
| status | TEXT | NO | Story state |
| first_event_at | TEXT | YES | UTC |
| last_event_at | TEXT | YES | UTC |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

---

# 32. `story_events` Table

A many-to-many relationship is recommended.

| Column | Type | Null | Description |
|---|---|---:|---|
| story_id | TEXT | NO | FK |
| event_id | TEXT | NO | FK |
| relevance_score | REAL | YES | Similarity |
| added_at | TEXT | NO | UTC |

Primary key:

```text
(story_id, event_id)
```

---

# 33. Story Grouping

Initial MVP may not automatically create stories.

The schema should still support future grouping.

Later:

```text
New Event
   |
   v
StoryMatcher
   |
   +--> Existing Story
   |
   +--> New Story
```

---

# 34. `rules` Table

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| name | TEXT | NO | Rule name |
| description | TEXT | YES | Description |
| enabled | INTEGER | NO | 0/1 |
| priority | INTEGER | NO | Evaluation order |
| conditions_json | TEXT | NO | Conditions |
| actions_json | TEXT | NO | Actions |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |

---

# 35. `rule_executions` Table

Purpose:

Audits rule behavior.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| rule_id | TEXT | NO | FK |
| event_id | TEXT | YES | FK |
| matched | INTEGER | NO | 0/1 |
| actions_executed_json | TEXT | YES | Actions |
| status | TEXT | NO | Result |
| error_message | TEXT | YES | Error |
| executed_at | TEXT | NO | UTC |

---

# 36. `content_jobs` Table

For future YouTube/content automation.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| event_id | TEXT | YES | FK |
| story_id | TEXT | YES | FK |
| job_type | TEXT | NO | Script/video/etc |
| status | TEXT | NO | Job state |
| target_duration_seconds | INTEGER | YES | Target duration |
| script_text | TEXT | YES | Generated script |
| metadata_json | TEXT | YES | Content metadata |
| created_at | TEXT | NO | UTC |
| updated_at | TEXT | NO | UTC |
| approved_at | TEXT | YES | UTC |
| published_at | TEXT | YES | UTC |
| failure_message | TEXT | YES | Error |

---

# 37. Content Job Status

```text
PENDING
GENERATING
REVIEW
APPROVED
REJECTED
PUBLISHING
PUBLISHED
FAILED
```

---

# 38. `audit_records` Table

Purpose:

Records important user/system actions.

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| id | TEXT | NO | UUID |
| action | TEXT | NO | Action name |
| actor | TEXT | YES | user/system |
| entity_type | TEXT | YES | Entity |
| entity_id | TEXT | YES | Entity UUID |
| correlation_id | TEXT | YES | Trace |
| details_json | TEXT | YES | Details |
| created_at | TEXT | NO | UTC |

Examples:

```text
TOPIC_CREATED
TOPIC_UPDATED
TOPIC_DISABLED
GMAIL_CONNECTED
GMAIL_DISCONNECTED
AI_PROFILE_CHANGED
EVENT_REPROCESSED
ATTACHMENT_DOWNLOADED
CONTENT_APPROVED
```

---

# 39. `application_settings` Table

Suggested schema:

| Column | Type | Null | Description |
|---|---|---:|---|
| key | TEXT | NO | Setting key |
| value_json | TEXT | NO | Setting value |
| value_type | TEXT | NO | Type |
| updated_at | TEXT | NO | UTC |

Primary key:

```text
key
```

Examples:

```text
notification.duration
notification.sound
notification.minimum_priority
attachment.download_enabled
attachment.maximum_size
retention.events_days
ai.default_provider
```

---

# 40. Secrets Are Not Application Settings

Do not store:

```text
OAuth refresh tokens
API keys
AWS access keys
Passwords
Client secrets
```

in `application_settings`.

Secrets must use the secure credential mechanism defined by the security architecture.

---

# 41. Index Strategy

Important indexes should include:

```text
intelligence_events(source_id, external_id)
intelligence_events(topic_id, occurred_at)
intelligence_events(received_at)
intelligence_events(content_hash)
intelligence_events(status)
intelligence_events(priority)

processing_records(status, next_retry_at)
processing_attempts(processing_record_id)

ai_analyses(event_id)
ai_analyses(ai_profile_id, created_at)

attachments(event_id)
attachments(download_status)

notifications(status, created_at)
notifications(topic_id, created_at)

stories(topic_id, last_event_at)
story_events(event_id)

rules(enabled, priority)

audit_records(entity_type, entity_id, created_at)
```

---

# 42. Search Index

For SQLite, full-text search should be considered for:

```text
Subject
Content
AI Summary
AI Headline
Entities
```

A future FTS5 virtual table may be used.

Conceptually:

```text
event_search
-------------
event_id
title
content
summary
entities
```

The search index must remain rebuildable from canonical data.

---

# 43. Search Index Principle

The search index is derived data.

Therefore:

```text
Canonical Database
       |
       v
Search Index
```

The application must not treat the search index as the only copy of an event.

---

# 44. Foreign Key Rules

Foreign keys must be enabled.

Recommended deletion behavior:

### Topics

Do not cascade-delete historical events automatically.

### Sources

Do not delete historical events merely because a source is removed.

### Events

Dependent records may cascade only when safe and explicitly intended.

### Stories

Deleting a story should normally unlink events rather than delete them.

---

# 45. Soft Delete

For configuration entities such as:

```text
Source
Topic
AI Profile
Rule
```

prefer:

```text
enabled = 0
```

or an explicit lifecycle status over immediate physical deletion.

This preserves history.

---

# 46. Event Retention

Event retention should be configurable.

Possible policies:

```text
7 days
30 days
90 days
365 days
Forever
```

The default will be determined during product configuration.

---

# 47. Attachment Retention

Attachments may have a shorter retention period than event metadata because they can consume significant disk space.

Example:

```text
Events: 365 days
Attachments: 30 days
```

The exact default is configurable.

---

# 48. AI Result Retention

AI summaries should generally remain available as long as the corresponding event remains retained.

When an event is deleted, dependent AI results should be handled according to the retention policy.

---

# 49. Audit Retention

Audit records should generally have a longer retention period than temporary processing records.

---

# 50. Processing Attempt Retention

Detailed processing attempts can eventually be pruned while preserving the final event status.

Example:

```text
Event:
COMPLETED

Detailed attempts:
retain 90 days
```

---

# 51. Cleanup Architecture

Cleanup should be performed by a controlled maintenance task.

Conceptually:

```text
MaintenanceService
      |
      +--> Event cleanup
      +--> Attachment cleanup
      +--> Processing cleanup
      +--> Audit retention
      +--> Search index maintenance
```

Cleanup must not run uncontrolled SQL from the UI.

---

# 52. Backup Strategy

The application should support backup of:

```text
SQLite database
Topic configuration
AI profiles
Rules
Settings
```

Attachments may be backed up separately.

---

# 53. SQLite Backup

Backup should use a safe SQLite-aware mechanism rather than blindly copying the live database while writes are occurring.

The implementation must account for WAL mode if enabled.

---

# 54. Restore Strategy

Restore should:

1. Stop relevant application operations.
2. Validate backup.
3. Preserve current database as a safety copy.
4. Restore database.
5. Run migrations if necessary.
6. Validate schema.
7. Restart processing.

---

# 55. Migration Strategy

Every schema change must be represented by a migration.

Example:

```text
001_initial_schema
002_add_ai_profiles
003_add_processing_attempts
004_add_stories
005_add_content_jobs
```

Migration files must be version-controlled.

---

# 56. Migration Rules

A migration must:

- Be deterministic.
- Be tested.
- Have a clear version.
- Not silently delete user data.
- Provide a recovery strategy.
- Be compatible with supported upgrade paths.

---

# 57. Database Transactions

Transactions are required for state changes that must be atomic.

Example:

```text
Event:
AI_COMPLETED
+
AIAnalysis:
created
+
ProcessingRecord:
updated
```

These should be committed consistently.

---

# 58. Event Processing Transaction Boundary

A recommended boundary:

```text
BEGIN
    update processing state
    save AI analysis
    update event priority/status
    create notification record if required
COMMIT
```

Actual transaction boundaries may be adjusted based on concurrency behavior.

---

# 59. Concurrency

SQLite supports concurrent reads but write concurrency is limited.

The application should therefore:

- Keep transactions short.
- Avoid holding write transactions during AI/network calls.
- Perform AI calls outside database transactions.
- Serialize or coordinate writes through a controlled persistence layer.

Never:

```text
BEGIN TRANSACTION
    call AI
    wait 10 seconds
COMMIT
```

Instead:

```text
AI call
   |
   v
short DB transaction
```

---

# 60. Database Access Rule

Only the persistence/infrastructure layer may directly access SQLite.

Forbidden:

```text
UI -> SQL
Application -> SQL
Domain -> SQL
```

Allowed:

```text
Application -> Repository -> SQLite
```

---

# 61. ORM Considerations

An ORM may be used, but the domain model should remain independent of ORM models.

Recommended separation:

```text
Domain Entity
      |
      v
Mapper
      |
      v
ORM Model
      |
      v
SQLite
```

---

# 62. JSON Column Policy

JSON is appropriate for:

```text
Provider-specific metadata
AI structured sections that may evolve
Topic policy configuration
Rule conditions/actions
Flexible settings
```

JSON should not be used merely to avoid designing relational columns.

Frequently queried fields should remain explicit columns.

---

# 63. Sensitive Email Content

Email content may contain sensitive information.

The database design must support configurable retention.

The application should avoid storing unnecessary duplicate copies of the same content.

---

# 64. Raw Provider Data

Raw Gmail/API responses should not be stored by default unless required for diagnostics or recovery.

If stored:

- Retention must be controlled.
- Sensitive data must be considered.
- Storage size must be monitored.

---

# 65. Database Size Management

The application should expose basic database statistics:

```text
Database size
Event count
Attachment size
AI analysis count
Notification count
```

This helps users manage long-running installations.

---

# 66. Integrity Checks

The application should periodically or manually support database integrity checks.

Examples:

```text
SQLite integrity check
Foreign key check
Missing attachment references
Orphan detection
```

---

# 67. Orphan Handling

The system should detect records such as:

```text
AIAnalysis without Event
Attachment without Event
Notification without Event
StoryEvent without Story
```

Orphans should normally be prevented through foreign keys.

---

# 68. Data Deletion

Deletion operations should be explicit.

Example:

```text
Delete Topic
```

means:

```text
Stop monitoring topic
```

not:

```text
Delete all historical events
```

Historical deletion should require a separate explicit action.

---

# 69. Event Purge

A purge operation may support:

```text
Delete events older than X days
```

The user must be warned about irreversible deletion.

---

# 70. Database Security

The SQLite database is local but should still be treated as sensitive.

The application should consider:

- Windows user account protection.
- File permissions.
- Backup security.
- Optional future database encryption.

Database encryption is not required for the first MVP unless the threat model requires it.

---

# 71. Multi-Account Future

The schema should permit multiple source accounts later.

Example:

```text
sources
    |
    +-- Gmail account A
    +-- Gmail account B
```

Topic configuration references the appropriate source.

---

# 72. Multi-User Future

If the product becomes multi-user, the future schema may add:

```text
users
user_topics
user_settings
user_sources
```

The MVP does not need these tables.

The current design should avoid making this future migration unnecessarily difficult.

---

# 73. Database-to-Domain Mapping

The database is persistence, not the domain model.

Example:

```text
DB row:
topic_id
name
source_id
ai_profile_id
priority_policy_json

        |
        v

Topic entity
```

Mapping should be explicit.

---

# 74. Database Repository Examples

Expected repositories:

```text
SourceRepository
TopicRepository
AIProfileRepository
EventRepository
ProcessingRepository
AIAnalysisRepository
AttachmentRepository
NotificationRepository
StoryRepository
RuleRepository
ContentJobRepository
AuditRepository
SettingsRepository
```

---

# 75. Repository Query Patterns

Common queries include:

```text
Find event by external ID
Find events by topic
Find recent events
Find pending processing
Find retryable processing
Find notifications pending display
Find active topics
Find active AI profile version
Search events
Find story events
```

Indexes must support these patterns.

---

# 76. Pending Work Query

The recovery process needs an efficient query for:

```text
status IN (
    RECEIVED,
    AI_PENDING,
    RETRY_PENDING,
    NOTIFICATION_PENDING
)
```

and:

```text
next_retry_at <= now
```

where applicable.

---

# 77. Notification Queue Persistence

Notification queue state should be persisted before attempting display when reliable recovery is required.

This prevents:

```text
Event persisted
Application crashes
Notification request lost
```

---

# 78. Processing Recovery Query

On startup:

```text
Find processing records where:
status = PROCESSING
```

These can be transitioned safely to:

```text
RETRY_PENDING
```

according to the recovery policy.

---

# 79. AI Usage Data

AI usage should be stored when provider information permits.

Useful fields:

```text
provider
model
input_tokens
output_tokens
latency_ms
estimated_cost
```

This supports future cost monitoring.

---

# 80. Cost Data

`estimated_cost` may be stored as a numeric value.

However, cost calculations must be treated as estimates unless directly supplied by the provider.

---

# 81. Database Design for Future Video Pipeline

The database must be capable of representing:

```text
Story
  |
  +--> ContentJob
          |
          +--> Script
          +--> Voice
          +--> Visuals
          +--> Video
          +--> Thumbnail
          +--> Publish
```

Future `content_assets` can reference generated files.

---

# 82. Future `content_assets` Table

Potential future schema:

```text
content_assets
-------------------------
id
content_job_id
asset_type
filename
storage_reference
mime_type
size_bytes
duration_seconds
metadata_json
created_at
```

Not required for MVP.

---

# 83. Database Design for YouTube Publishing

Future publishing records may include:

```text
youtube_video_id
title
description
privacy_status
published_at
url
```

These should be added through a publishing table rather than overloading `content_jobs`.

---

# 84. Auditability

Important database changes should be auditable.

Example:

```text
Topic:
TRUMP

Old profile:
General News v1

New profile:
Trading/Geopolitics v2
```

The audit record should make this change traceable.

---

# 85. Schema Naming Rules

Use:

```text
snake_case
```

for database names.

Examples:

```text
intelligence_events
ai_profiles
processing_records
created_at
updated_at
```

---

# 86. Primary Key Naming

Use:

```text
<entity>_id
```

for foreign keys.

Examples:

```text
topic_id
source_id
event_id
story_id
ai_profile_id
```

---

# 87. Boolean Naming

SQLite boolean fields should use:

```text
enabled
is_active
is_current
```

stored as integer 0/1.

---

# 88. Nullability Principle

Use `NULL` when the information is genuinely unknown or not yet available.

Do not use arbitrary values such as:

```text
""
0
"UNKNOWN"
```

when `NULL` has the correct semantic meaning.

---

# 89. Default Values

Defaults should be applied deliberately.

Examples:

```text
enabled = 1
attempt_count = 0
created_at = now
```

But business-critical defaults should be defined in application/domain code rather than duplicated inconsistently across database and application layers.

---

# 90. Schema Constraints

Where practical, enforce:

```text
NOT NULL
UNIQUE
FOREIGN KEY
CHECK
```

at the database layer.

Application validation remains necessary.

---

# 91. Database Design for Idempotency

The most important idempotency constraint is:

```text
UNIQUE(source_id, external_id)
```

This protects against:

```text
Duplicate Pub/Sub notification
Duplicate Gmail retrieval
Application retry
Application restart
```

---

# 92. Database Design for Recovery

Recovery depends on persistent state.

At minimum the database must preserve:

```text
Event
Processing status
Attempt count
Last error
Next retry
AI result
Notification status
```

This makes restart recovery possible.

---

# 93. Database Design for Real-Time Operation

The database should never become the real-time event transport itself.

Use:

```text
Pub/Sub
   |
   v
Application Worker
   |
   v
SQLite
```

not:

```text
SQLite polling every 30 seconds
```

---

# 94. Database Design for Notifications

Notification persistence separates:

```text
Intelligence completed
```

from:

```text
Notification displayed
```

This is important because notification delivery can fail independently.

---

# 95. Database Design for AI

AI results are persisted separately from source events.

This allows:

```text
Re-analysis
Prompt versioning
Provider comparison
AI history
Cost analysis
```

without duplicating the source event.

---

# 96. Re-analysis

Future feature:

```text
Existing Event
     |
     v
New AI Profile
     |
     v
New AI Analysis
```

The original analysis should remain available unless explicitly deleted.

---

# 97. Current Analysis

If multiple AI analyses exist, the application should have a deterministic way to select the current one.

Possible future fields:

```text
is_current
supersedes_analysis_id
```

---

# 98. Database Design Quality Rules

Before adding a new table, ask:

1. What domain concept does it represent?
2. Why cannot it be represented by an existing table?
3. What is its lifecycle?
4. What is its primary key?
5. What are its foreign keys?
6. What must be unique?
7. What needs indexing?
8. What is its retention policy?
9. Can it be reconstructed?
10. Is it canonical data or derived data?

---

# 99. MVP Tables

The first database migration should prioritize:

```text
sources
topics
ai_profiles
ai_profile_versions
intelligence_events
processing_records
processing_attempts
ai_analyses
notifications
attachments
application_settings
audit_records
```

---

# 100. Post-MVP Tables

Add later:

```text
stories
story_events
rules
rule_executions
content_jobs
content_assets
```

Only introduce them when their functionality is being implemented.

---

# 101. Initial Migration

The first migration should create:

```text
001_initial_schema
```

with the MVP tables and required indexes/constraints.

It should also:

```text
enable foreign keys
configure appropriate SQLite pragmas
create schema metadata
```

---

# 102. SQLite Pragmas

The application should explicitly configure required SQLite behavior.

Potential settings include:

```text
foreign_keys = ON
journal_mode = WAL
busy_timeout = appropriate value
```

Exact production values must be validated through integration testing.

---

# 103. Write Concurrency Strategy

Because SQLite has limited write concurrency:

```text
AI processing
Network calls
Attachment downloads
```

must happen outside database write transactions.

Database writes should be short and controlled.

---

# 104. Database Connection Management

The persistence layer should manage SQLite connections.

UI and domain code must not create independent database connections.

---

# 105. Thread Safety

The database access strategy must be compatible with the chosen Python concurrency model.

If worker threads are used:

- Connections must be managed appropriately.
- Thread-unsafe connection sharing must be avoided.
- Transaction boundaries must be explicit.

---

# 106. Database Health

The application should expose:

```text
Database Connected
Database Size
Schema Version
Last Integrity Check
Pending Writes
```

where practical.

---

# 107. Database Failure

If the database becomes unavailable or corrupted:

1. Stop unsafe writes.
2. Report the error.
3. Preserve recoverable external events where possible.
4. Prevent false `COMPLETED` states.
5. Provide recovery instructions.
6. Keep the UI responsive.

---

# 108. Backup Before Migration

For production updates involving schema migrations:

```text
Backup
  |
  v
Migration
  |
  v
Integrity Check
  |
  v
Application Start
```

If migration fails, recovery must be possible.

---

# 109. Final Database Architecture

```text
                    SQLite
                       |
       +---------------+----------------+
       |               |                |
       v               v                v
 Configuration      Intelligence     Operations
       |               |                |
       |               +--> Events      +--> Processing
       |               +--> AI          +--> Notifications
       |               +--> Attachments +--> Audit
       |               +--> Stories     +--> Settings
       |
       +--> Sources
       +--> Topics
       +--> AI Profiles
       +--> Rules
```

---

# 110. Final Principle

The database is the **durable memory of InsightFlow AI**.

The design must ensure that:

```text
An event received
      |
      v
is not silently lost.

An AI result created
      |
      v
can be traced to its source and prompt.

A notification requested
      |
      v
can be recovered if the application crashes.

A topic changed
      |
      v
can be audited.

A future AI model introduced
      |
      v
does not destroy historical analysis.
```

The database must therefore prioritize **durability, traceability, idempotency, recoverability, and controlled growth** over premature complexity.
