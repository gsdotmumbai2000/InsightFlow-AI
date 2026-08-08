# InsightFlow AI — Interface and API Contracts

**Document:** `10_Interface_and_API_Contracts.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `04_System_Architecture.md`, `05_System_Design.md`, `06_Database_Design.md`, `08_SOLID_and_Design_Patterns.md`, `09_Project_Structure_and_Coding_Standards.md`

---

# 1. Purpose

This document defines the contracts between the major components of InsightFlow AI.

The purpose is to ensure that:

- Components can be developed independently.
- Cursor/Codex/other AI coding agents have explicit interfaces to implement.
- External providers do not leak into the core application.
- UI code does not depend on infrastructure.
- AI providers can be replaced.
- Gmail can eventually be replaced or supplemented by other sources.
- Notifications can be replaced.
- Database implementations can be replaced.
- Future YouTube/content functionality can be added without modifying the monitoring core.

The contracts defined here are more important than any specific implementation.

An implementation may change internally as long as it preserves these contracts.

---

# 2. Contract Philosophy

The architecture follows:

```text
External System
      |
      v
Adapter
      |
      v
Application Port / Contract
      |
      v
Application Use Case
      |
      v
Domain
```

The reverse direction is:

```text
Domain/Application
      |
      v
Port / Interface
      ^
      |
Infrastructure Adapter
```

---

# 3. Contract Categories

Contracts are divided into:

```text
1. Domain contracts
2. Application contracts
3. Infrastructure ports
4. External provider contracts
5. UI contracts
6. Internal event contracts
7. Persistence contracts
8. Error contracts
9. State contracts
10. Future content contracts
```

---

# 4. Contract Rules

Every contract must define:

```text
Purpose
Input
Output
Errors
Side effects
Idempotency
Concurrency expectations
```

Where relevant.

---

# 5. Contract Stability

Once a contract is used by multiple modules:

```text
Do not casually change it.
```

Breaking changes require:

```text
Documentation update
Implementation update
Tests
Migration if required
```

---

# 6. Domain Contract — Intelligence Event

The central business object is:

```text
IntelligenceEvent
```

Conceptually:

```text
IntelligenceEvent
├── id
├── source_id
├── topic_id
├── external_id
├── thread_id
├── received_at
├── source_published_at
├── subject
├── headline
├── raw_content_reference
├── normalized_content
├── language
├── processing_status
├── priority
├── user_status
└── metadata
```

The exact persistence representation is defined by `06_Database_Design.md`.

---

# 7. Event Identity Contract

Every external event must have an internal identity:

```text
event_id
```

and an external identity:

```text
external_event_id
```

The combination needed for deduplication must be deterministic.

Example:

```text
source_id + external_id
```

---

# 8. Event Creation Contract

Input:

```text
NormalizedSourceEvent
```

Output:

```text
IntelligenceEvent
```

Rules:

- Validate required fields.
- Resolve topic.
- Generate internal ID.
- Preserve source identifiers.
- Set initial processing state.
- Do not invoke AI during entity construction.

---

# 9. Topic Contract

A topic represents what the user wants to monitor.

Conceptually:

```text
Topic
├── id
├── name
├── description
├── enabled
├── source_configuration
├── ai_profile_id
├── notification_policy
├── attachment_policy
└── metadata
```

Examples:

```text
TRUMP
IRAN
MODI
CELEBRITY_X
COMPANY_Y
```

These are data, not code.

---

# 10. Topic Resolver Contract

```text
TopicResolver
```

Purpose:

```text
Determine which configured topic(s) apply to an incoming source event.
```

Input:

```text
NormalizedSourceEvent
```

Output:

```text
list[TopicMatch]
```

A match may contain:

```text
topic_id
confidence
match_reason
```

---

# 11. Topic Matching Rule

The resolver must not assume that all topics are named entities.

A topic may be based on:

```text
Gmail label
Keyword
Source
User rule
Combination
```

The MVP may use Gmail label mapping as the primary mechanism.

---

# 12. Source Provider Contract

```python
class SourceProvider(Protocol):
    def get_source_identity(self) -> SourceIdentity: ...
    def get_events(self, request: EventFetchRequest) -> list[SourceEvent]: ...
    def get_event(self, external_id: str) -> SourceEvent: ...
```

The exact Python signatures may evolve during implementation.

The semantic contract must remain stable.

---

# 13. Source Provider Responsibilities

A source provider may:

- Connect to an external source.
- Retrieve events.
- Retrieve individual messages.
- Retrieve source metadata.
- Translate provider-specific responses.

It must not:

- Run AI analysis.
- Decide application priority.
- Show desktop notifications.
- Write directly to UI.

---

# 14. Gmail Provider Contract

The Gmail provider implements the source contract.

It is responsible for:

```text
OAuth
Gmail API
Labels
Messages
Threads
Attachments
History
Watch configuration
```

Gmail-specific IDs must not leak into unrelated domain logic.

---

# 15. Normalized Source Event

The Gmail adapter converts a Gmail message into:

```text
NormalizedSourceEvent
```

Conceptually:

```text
NormalizedSourceEvent
├── source_type
├── source_id
├── external_id
├── external_thread_id
├── sender
├── recipients
├── subject
├── body_text
├── body_html_reference
├── published_at
├── received_at
├── labels
├── attachments
└── metadata
```

---

# 16. Source Event Contract

The source event must preserve enough information to:

```text
Create an intelligence event
Open the original source
Download attachments
Perform AI analysis
Deduplicate
Audit processing
```

---

# 17. Source Event Idempotency

The same external source event may be delivered multiple times.

The application must treat repeated delivery as safe.

Example:

```text
Gmail event A
Gmail event A
Gmail event A
```

must result in:

```text
One intelligence event
```

unless the source explicitly identifies them as distinct.

---

# 18. AI Provider Contract

The central AI abstraction is:

```text
AIProvider
```

Conceptual contract:

```python
class AIProvider(Protocol):
    def analyze(self, request: AIRequest) -> AIResponse: ...
```

---

# 19. AI Request

Conceptually:

```text
AIRequest
├── event_id
├── topic
├── profile
├── profile_version
├── source_content
├── context
├── requested_output
└── metadata
```

---

# 20. AI Request Rules

The request must contain:

```text
Relevant source content
AI profile instructions
Topic context
Expected output contract
```

The provider must not need access to the database.

---

# 21. AI Response

The provider returns a provider-neutral response:

```text
AIResponse
├── provider
├── model
├── request_id
├── content
├── structured_output
├── usage
├── latency
└── metadata
```

---

# 22. AI Analysis Contract

The application converts the provider response into:

```text
AIAnalysis
```

Possible fields:

```text
summary
why_it_matters
what_to_watch
facts
interpretation
market_impact
entities
sentiment
confidence
```

Not every AI profile needs every field.

---

# 23. AI Output Schema Contract

AI profiles define expected output.

Example:

```json
{
  "summary": "Short summary",
  "why_it_matters": "Explanation",
  "what_to_watch": [
    "Signal 1",
    "Signal 2"
  ],
  "market_impact": {
    "direction": "uncertain",
    "assets": [
      "crude oil",
      "equities"
    ],
    "reason": "..."
  },
  "confidence": 0.82
}
```

This is illustrative, not a mandatory final JSON schema.

The production schema must be formally versioned.

---

# 24. AI Output Validation

Every structured AI response must pass:

```text
AIOutputValidator
```

before it becomes trusted application data.

Flow:

```text
AI Provider
    |
    v
Raw AI Response
    |
    v
Parser
    |
    v
Schema Validator
    |
    v
Validated AI Analysis
```

---

# 25. AI Failure Contract

If AI fails:

```text
Do not lose the intelligence event.
```

The event remains stored.

Processing becomes:

```text
AI_RETRY_PENDING
```

or:

```text
AI_FAILED
```

depending on retry policy.

---

# 26. AI Provider Error Types

Examples:

```text
AIProviderUnavailableError
AIAuthenticationError
AIRequestRejectedError
AIResponseInvalidError
AIResponseTimeoutError
AIQuotaExceededError
```

Each must be classified as:

```text
Retryable
Non-retryable
```

---

# 27. AI Provider Idempotency

AI processing may be retried.

The application must retain:

```text
event_id
analysis_attempt
profile_version
provider
model
```

so each analysis attempt is traceable.

---

# 28. AI Profile Contract

An AI profile defines how a topic should be analyzed.

Conceptually:

```text
AIProfile
├── id
├── name
├── description
├── system_prompt
├── output_schema
├── model_preferences
├── version
└── enabled
```

---

# 29. AI Profile Examples

Generic examples:

```text
General News
Trading / Geopolitics
Entertainment
Technology
Company Monitoring
Sports
```

The application must not hardcode these profiles.

---

# 30. Prompt Builder Contract

```text
PromptBuilder
```

Input:

```text
AIProfile
Topic
SourceEvent
Context
```

Output:

```text
AIRequest
```

The prompt builder must not call the AI provider.

---

# 31. AI Model Selection Contract

```text
AIModelSelector
```

may determine:

```text
Provider
Model
Temperature/settings
Token limits
```

based on configuration/profile.

The event processor should not contain provider-specific selection logic.

---

# 32. Priority Engine Contract

```text
PriorityEngine
```

Input:

```text
IntelligenceEvent
AIAnalysis
Topic
Rules
```

Output:

```text
Priority
```

Possible values:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 33. Priority Rules

Priority must be deterministic after required AI signals are available.

AI may provide signals, but final notification policy must remain application-controlled.

---

# 34. Notification Provider Contract

```python
class NotificationProvider(Protocol):
    def notify(self, notification: NotificationRequest) -> NotificationResult: ...
```

---

# 35. Notification Request

Conceptually:

```text
NotificationRequest
├── notification_id
├── event_id
├── topic
├── priority
├── title
├── summary
├── source_url
├── duration
├── sound
└── metadata
```

---

# 36. Windows Notification Contract

The Windows notification adapter is responsible for:

```text
Bottom-right positioning
Animation
Fade in/out
Display duration
User interaction
Dismissal
```

The application should not directly control Windows GUI APIs.

---

# 37. Notification Result

```text
NotificationResult
├── notification_id
├── status
├── displayed_at
├── dismissed_at
└── error
```

Possible statuses:

```text
QUEUED
DISPLAYED
DISMISSED
EXPIRED
FAILED
```

---

# 38. Notification Policy Contract

```text
NotificationPolicy
```

Input:

```text
Event
Priority
Topic
UserSettings
CurrentTime
```

Output:

```text
NotificationDecision
```

Example:

```text
should_notify = true
duration = 10
sound = false
reason = "HIGH priority"
```

---

# 39. Quiet Hours Contract

Quiet hours affect notification delivery, not event processing.

Example:

```text
Event received during quiet hours
        |
        v
Process normally
        |
        v
Store normally
        |
        v
Notification suppressed
```

---

# 40. Attachment Contract

```text
Attachment
├── id
├── event_id
├── filename
├── mime_type
├── size
├── external_id
├── download_status
├── processing_status
└── storage_reference
```

---

# 41. Attachment Downloader Contract

```text
AttachmentDownloader
```

Input:

```text
AttachmentDownloadRequest
```

Output:

```text
AttachmentDownloadResult
```

Responsibilities:

- Download.
- Validate size.
- Validate source identity.
- Store safely.
- Report status.

---

# 42. Attachment Processor Contract

```python
class AttachmentProcessor(Protocol):
    def supports(self, mime_type: str, filename: str) -> bool: ...
    def process(self, request: AttachmentProcessRequest) -> AttachmentProcessResult: ...
```

Implementations may include:

```text
PDF
Excel
CSV
Text
Image
ZIP
```

---

# 43. Attachment Security Contract

Before processing:

```text
Validate filename
Validate size
Validate type
Validate path
Apply security policy
```

ZIP extraction must prevent path traversal.

---

# 44. Storage Contract

```text
AttachmentStorage
```

Conceptual:

```python
store(...)
open(...)
delete(...)
exists(...)
```

The domain must not know the filesystem implementation.

---

# 45. Secret Store Contract

```text
SecretStore
```

Examples:

```text
get_secret(name)
set_secret(name, value)
delete_secret(name)
```

The preferred Windows implementation should use the operating system's secure credential mechanism.

---

# 46. Clock Contract

```text
Clock
```

Purpose:

```text
Provide current time.
```

Production:

```text
SystemClock
```

Tests:

```text
FakeClock
```

---

# 47. Event Repository Contract

```python
class EventRepository(Protocol):
    def add(self, event: IntelligenceEvent) -> None: ...
    def get(self, event_id: EventId) -> IntelligenceEvent | None: ...
    def find_by_external_id(...): ...
    def update(self, event: IntelligenceEvent) -> None: ...
```

Exact method signatures may be refined during implementation.

---

# 48. Topic Repository Contract

Responsibilities:

```text
Create
Find
Update
List enabled topics
Find by source/label
```

---

# 49. AI Analysis Repository Contract

Responsibilities:

```text
Save analysis
Find latest analysis
Find analysis history
Find by event
```

---

# 50. Notification Repository Contract

Responsibilities:

```text
Create notification
Update notification state
List notifications
Find pending notifications
```

---

# 51. Story Repository Contract

Future contract:

```text
Create story
Update story
Find story
List stories
Add event to story
```

---

# 52. Content Job Repository Contract

Future:

```text
Create content job
Update status
Get job
List pending jobs
```

---

# 53. Unit of Work Contract

Conceptually:

```python
class UnitOfWork(Protocol):
    events: EventRepository
    topics: TopicRepository
    analyses: AIAnalysisRepository
    notifications: NotificationRepository

    def __enter__(self): ...
    def __exit__(self, exc_type, exc, traceback): ...
    def commit(self): ...
    def rollback(self): ...
```

---

# 54. Unit of Work Rules

Transactions must be:

```text
Short
Atomic
Explicit
```

Do not keep a transaction open during:

```text
AI calls
Gmail calls
Attachment downloads
Notification display
```

---

# 55. Processing Queue Contract

```text
ProcessingQueue
```

Input:

```text
ProcessEventCommand
```

Output:

```text
QueuedJob
```

The queue must support:

```text
enqueue
dequeue
acknowledge
retry
dead-letter/failure
```

where applicable.

---

# 56. Processing Worker Contract

```text
EventWorker
```

Responsibilities:

```text
Receive job
Validate
Execute use case
Handle success/failure
Acknowledge/retry
```

Workers must have bounded concurrency.

---

# 57. Gmail Real-Time Event Contract

The external Gmail/Google event should eventually produce:

```text
GmailNotification
```

Conceptually:

```text
GmailNotification
├── email_address
├── history_id
└── received_at
```

The notification itself is not necessarily the complete email.

The application must use the history identifier to retrieve the relevant changes.

---

# 58. Pub/Sub Contract

The Pub/Sub adapter should expose:

```text
PubSubMessage
```

and translate it into:

```text
GmailChangeNotification
```

It should acknowledge the message only according to the processing/acknowledgement policy.

---

# 59. Pub/Sub Error Contract

Errors must distinguish:

```text
Malformed message
Temporary provider error
Authentication error
Application processing failure
```

Retry behavior must depend on classification.

---

# 60. Gmail Watch Contract

The Gmail monitoring service should expose operations conceptually equivalent to:

```text
start_watch()
renew_watch()
stop_watch()
get_watch_status()
```

The exact Gmail API implementation remains inside infrastructure.

---

# 61. Real-Time Monitoring Contract

```text
MonitoringService
```

Responsibilities:

```text
Start monitoring
Stop monitoring
Reconnect
Renew watch
Expose status
Handle incoming notifications
```

It must not:

```text
Perform AI analysis directly
Update UI widgets directly
Execute SQL directly
```

---

# 62. Monitoring Status Contract

Possible states:

```text
DISCONNECTED
CONNECTING
CONNECTED
ACTIVE
RECONNECTING
PAUSED
ERROR
STOPPED
```

---

# 63. Monitoring Status Object

```text
MonitoringStatus
├── state
├── provider
├── account
├── started_at
├── last_event_at
├── last_error
└── next_renewal_at
```

---

# 64. Application Event Bus Contract

An internal event bus may expose:

```text
publish(event)
subscribe(event_type, handler)
unsubscribe(...)
```

It should be used for decoupled reactions.

---

# 65. Internal Event Examples

```text
IntelligenceEventReceived
AIAnalysisStarted
AIAnalysisCompleted
NotificationRequested
NotificationDisplayed
MonitoringStatusChanged
AttachmentDownloaded
StoryUpdated
```

---

# 66. Event Bus Rule

The event bus must not replace normal method calls.

Use:

```text
Direct call
```

when a caller requires a direct response.

Use:

```text
Event
```

when the publisher is announcing something that multiple independent components may react to.

---

# 67. Event Delivery Rule

Internal events should be:

```text
Typed
Observable
Traceable
```

where practical.

---

# 68. UI Application Service Contract

The presentation layer should communicate with application use cases.

Example:

```text
DashboardViewModel
    |
    v
GetDashboardQuery
```

not:

```text
DashboardView
    |
    v
SQLite
```

---

# 69. Dashboard Query Contract

Input:

```text
DashboardQuery
├── date_range
├── topic_filter
└── priority_filter
```

Output:

```text
DashboardDTO
├── system_status
├── live_events
├── important_events
├── activity
├── processing_status
└── unread_count
```

---

# 70. Search Contract

```text
SearchEventsQuery
```

Input:

```text
query
topic
priority
date_from
date_to
source
page
page_size
```

Output:

```text
SearchResult
├── items
├── total_count
├── page
└── page_size
```

---

# 71. Event Details Query

Input:

```text
event_id
```

Output:

```text
EventDetailsDTO
```

including:

```text
event
topic
AI analyses
attachments
notifications
source information
processing history
```

---

# 72. Topic Management Contract

Commands:

```text
CreateTopic
UpdateTopic
EnableTopic
DisableTopic
PauseTopic
ResumeTopic
DeleteTopic
```

Historical intelligence should not be deleted when a topic is merely disabled or paused.

---

# 73. Topic Creation Request

Conceptually:

```text
CreateTopicRequest
├── name
├── description
├── source_id
├── source_configuration
├── ai_profile_id
├── notification_policy
└── attachment_policy
```

---

# 74. Topic Validation

Validation should ensure:

```text
Name is non-empty
Source configuration is valid
AI profile exists
Notification policy is valid
Attachment policy is valid
```

---

# 75. Reprocess AI Contract

```text
ReprocessAICommand
```

Input:

```text
event_id
ai_profile_id
optional_profile_version
```

Output:

```text
QueuedJob
```

The existing analysis must remain available until the new analysis succeeds.

---

# 76. Notification Command Contract

```text
RequestNotificationCommand
```

Input:

```text
event_id
priority
notification policy
```

Output:

```text
NotificationId
```

---

# 77. Source Opening Contract

```text
OpenSourceCommand
```

Input:

```text
event_id
```

Output:

```text
SourceReference
```

The presentation/infrastructure layer may then open the user's default browser.

---

# 78. Security Boundary

Opening a source must validate:

```text
URL
scheme
source type
```

Do not allow arbitrary command execution through source-opening functionality.

---

# 79. Attachment Download Command

```text
DownloadAttachmentCommand
```

Input:

```text
attachment_id
```

Output:

```text
AttachmentDownloadResult
```

---

# 80. Attachment Processing Command

```text
ProcessAttachmentCommand
```

Input:

```text
attachment_id
processor_type optional
```

Output:

```text
AttachmentProcessResult
```

---

# 81. Health Check Contract

```text
HealthCheck
```

Conceptually:

```python
def check() -> HealthStatus:
    ...
```

Implementations:

```text
DatabaseHealthCheck
GmailHealthCheck
AIHealthCheck
NotificationHealthCheck
StorageHealthCheck
```

---

# 82. Health Status Contract

```text
HealthStatus
├── component
├── status
├── checked_at
├── message
└── details
```

Statuses:

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

---

# 83. Configuration Contract

Configuration should be represented by typed objects.

Examples:

```text
ApplicationConfig
GmailConfig
AIConfig
NotificationConfig
AttachmentConfig
StorageConfig
LoggingConfig
```

---

# 84. Configuration Provider Contract

```text
ConfigurationProvider
```

Responsibilities:

```text
Load
Validate
Provide typed configuration
```

It must not expose raw secret values unnecessarily.

---

# 85. Audit Contract

```text
AuditService
```

Input:

```text
AuditRecord
```

Conceptually:

```text
AuditRecord
├── actor
├── action
├── entity_type
├── entity_id
├── timestamp
├── correlation_id
└── details
```

---

# 86. Error Contract

Application errors should be categorized.

```text
DomainError
ApplicationError
InfrastructureError
ProviderError
ValidationError
SecurityError
```

---

# 87. Error Translation

External:

```text
Google RefreshError
```

becomes:

```text
GmailAuthenticationError
```

External:

```text
Bedrock throttling
```

becomes:

```text
AIQuotaExceededError
```

The application should not depend on provider exception classes.

---

# 88. Retry Contract

Each retryable operation must define:

```text
Maximum attempts
Backoff
Retryable errors
Idempotency behavior
```

---

# 89. Idempotency Contract

Operations that can be retried must use stable identifiers.

Examples:

```text
source external ID
event ID
notification ID
content job ID
attachment ID
```

---

# 90. Correlation ID Contract

Every asynchronous workflow should carry:

```text
correlation_id
```

Example:

```text
Gmail notification
   |
   v
Correlation ID
   |
   +--> Event
   +--> AI request
   +--> Notification
   +--> Logs
```

---

# 91. API Contract Versioning

Internal contracts may initially be versioned through source control.

External/public APIs, if introduced later, must use explicit versioning:

```text
/v1/...
```

---

# 92. No REST Requirement for MVP

InsightFlow AI is primarily a desktop application.

A REST API is not required for the initial MVP.

If a local API becomes useful later, it must be introduced behind explicit contracts.

---

# 93. Local API Future Contract

Potential future API areas:

```text
/events
/topics
/notifications
/stories
/health
/content
```

This is future architecture only.

Do not implement until required.

---

# 94. YouTube Content Contract — Future

Future content pipeline:

```text
ContentJob
```

Conceptually:

```text
ContentJob
├── id
├── source_event_ids
├── story_id
├── content_type
├── target_duration
├── script
├── status
├── review_status
└── publishing_status
```

---

# 95. Script Generator Contract

```text
ScriptGenerator
```

Input:

```text
Story
AI analysis
target duration
content style
```

Output:

```text
VideoScript
```

---

# 96. Video Script Contract

```text
VideoScript
├── title
├── hook
├── scenes
├── narration
├── captions
├── source_references
└── estimated_duration
```

---

# 97. Human Review Contract

Content generation must support:

```text
DRAFT
REVIEW_REQUIRED
APPROVED
REJECTED
PUBLISHED
```

Initial implementation should require explicit approval before publishing.

---

# 98. Publisher Contract — Future

```text
Publisher
```

Input:

```text
ApprovedContent
```

Output:

```text
PublicationResult
```

Potential implementation:

```text
YouTubePublisher
```

The content pipeline must not directly call the YouTube API.

---

# 99. Contract for AI-Generated Trading Information

AI analysis may provide:

```text
Potential impact
Risk
What to watch
Scenario
```

It must not be treated as an authoritative trading instruction.

The application should display AI analysis as analysis, not guaranteed prediction.

---

# 100. Data Provenance Contract

Every AI analysis must be traceable to:

```text
event_id
source
topic
AI profile
profile version
provider
model
analysis timestamp
```

---

# 101. AI Reproducibility Contract

If an analysis is regenerated:

```text
Previous analysis remains in history.
```

The new analysis receives a new attempt/version record.

---

# 102. Contract for Source Facts

The AI response should distinguish:

```text
source-supported facts
```

from:

```text
AI interpretation
```

The UI should preserve this distinction.

---

# 103. Contract for Market Impact

Market impact is optional.

If the selected AI profile does not produce market analysis:

```text
market_impact = null
```

Do not invent it.

---

# 104. Contract for Missing AI Fields

Missing optional AI fields must be represented explicitly.

Example:

```text
what_to_watch = []
market_impact = None
confidence = None
```

Avoid fake values.

---

# 105. Contract for Unknown Values

Do not convert unknown into:

```text
0
false
"none"
```

unless the domain explicitly defines that meaning.

Use nullable/optional fields.

---

# 106. Contract for Pagination

Pagination should be explicit.

Input:

```text
page
page_size
```

or:

```text
cursor
limit
```

The chosen strategy should remain consistent across application queries.

---

# 107. Contract for Sorting

Sort fields must be validated against an allow-list.

Do not pass arbitrary UI strings into SQL ORDER BY clauses.

---

# 108. Contract for Filtering

Filters must be typed/validated before reaching repositories.

The UI must not construct raw SQL filters.

---

# 109. Contract for UI Live Updates

The presentation layer should receive typed application events.

Example:

```text
IntelligenceEventReceived
AIAnalysisCompleted
NotificationCreated
MonitoringStatusChanged
```

The ViewModel transforms them into UI state.

---

# 110. Live Event Contract

```text
LiveIntelligenceEvent
├── event_id
├── topic_id
├── priority
├── headline
├── summary
├── received_at
└── status
```

---

# 111. UI Notification Contract

The popup should receive only what it needs:

```text
NotificationViewModel
├── title
├── topic
├── priority
├── summary
├── event_id
├── source_url
├── duration
└── sound
```

It should not receive:

```text
Database connection
Gmail client
AI provider
```

---

# 112. Contract for UI Commands

Every important UI action should map to an application command/query.

Examples:

```text
OpenEvent
CreateTopic
PauseTopic
RetryAI
OpenSource
DownloadAttachment
ChangeSettings
```

---

# 113. Contract for UI Errors

Application errors should be translated to presentation messages.

Example:

```text
GmailAuthenticationError
```

becomes:

```text
"Gmail authorization has expired. Please reconnect your Google account."
```

---

# 114. Contract for Diagnostics

Diagnostics should expose:

```text
Component
Status
Last successful operation
Last error
Timestamp
```

but must not expose secrets.

---

# 115. Contract for Logging

Every provider boundary should log:

```text
start
success/failure
duration
correlation_id
```

without sensitive payloads.

---

# 116. Contract for Metrics

Future metrics may include:

```text
events_received_total
events_processed_total
events_failed_total
ai_requests_total
ai_failures_total
notifications_displayed_total
attachment_downloads_total
processing_latency
ai_latency
```

Metrics are observational and must not change business behavior.

---

# 117. Contract for Health and Monitoring

Health checks must not modify application state.

They should observe and report.

---

# 118. Contract for Shutdown

Application shutdown should be coordinated.

Conceptual:

```text
Stop accepting new work
      ↓
Stop real-time watcher/subscriber
      ↓
Finish/cancel active work according to policy
      ↓
Flush notifications/logs
      ↓
Close database
      ↓
Exit
```

---

# 119. Contract for Startup

Startup should:

```text
Load configuration
Validate environment
Initialize database
Initialize dependencies
Initialize UI
Connect/restore monitoring
Start workers
Expose health status
```

Startup failures should be explicit.

---

# 120. Contract for Graceful Degradation

If AI is unavailable:

```text
Monitoring continues.
Events are stored.
AI remains pending/retryable.
```

If notifications are unavailable:

```text
Monitoring continues.
Events are stored.
Notification status records failure.
```

If Gmail is unavailable:

```text
Historical local data remains available.
Monitoring status becomes ERROR/RECONNECTING.
```

---

# 121. Contract for Offline Operation

The application should continue to provide:

```text
Historical intelligence
Search
Topic configuration
Local settings
Diagnostics
```

when external services are unavailable.

Real-time monitoring obviously requires the external connection.

---

# 122. Contract for Graceful AI Provider Change

Changing AI provider must not change:

```text
IntelligenceEvent
AIAnalysis
Notification
Topic
```

contracts.

Only the provider implementation/configuration changes.

---

# 123. Contract for Future Multi-Source Monitoring

If RSS or other sources are added:

```text
SourceProvider
```

must produce the same normalized event contract.

---

# 124. Contract for Source Metadata

Every event should identify:

```text
source_type
source_id
external_id
source_url where available
```

---

# 125. Contract for User Actions

User actions should be auditable where appropriate.

Examples:

```text
Topic created
Topic disabled
AI reprocessed
Event marked important
History deleted
Settings changed
Content approved
Content published
```

---

# 126. Contract for Delete Operations

Delete operations must distinguish:

```text
Soft archive
Hard delete
Retention cleanup
```

The default should favor preserving historical intelligence.

---

# 127. Contract for Database Migration

Schema changes must be:

```text
Versioned
Repeatable
Tested
Reversible where practical
```

Application code must not silently create arbitrary missing tables at runtime.

---

# 128. Contract for External API Rate Limits

Provider adapters must translate rate limiting into typed retryable errors.

The application controls:

```text
Backoff
Concurrency
Retry
```

---

# 129. Contract for Provider Timeouts

Every network provider should have explicit timeout behavior.

No indefinite blocking.

---

# 130. Contract for Cancellation

Long-running provider operations should support cancellation where technically possible.

Cancellation should not corrupt persisted state.

---

# 131. Contract for Transaction Boundaries

Example:

```text
BEGIN
  create event
  update processing state
COMMIT

AI call

BEGIN
  save AI analysis
  update state
  create notification request
COMMIT
```

Do not keep database transactions open around AI/network calls.

---

# 132. Contract for Notification Ordering

For a single event:

```text
Event stored
      ↓
AI completed
      ↓
Priority determined
      ↓
Notification requested
```

Notification must not be generated from an incomplete analysis unless explicitly configured.

---

# 133. Contract for Early Notification

The application may optionally support:

```text
Immediate "New event received"
```

followed later by:

```text
AI summary notification
```

This must be an explicit notification policy, not accidental behavior.

---

# 134. Contract for Duplicate Notifications

Repeated processing of the same event must not generate duplicate user notifications unless the notification policy explicitly permits them.

---

# 135. Contract for Topic Isolation

A topic must not accidentally receive another topic's events.

Every event-to-topic association must be explicit and traceable.

---

# 136. Contract for AI Profile Isolation

An AI profile change affects new analyses.

Historical analyses retain their original:

```text
profile version
```

---

# 137. Contract for Configuration Changes

Changing notification settings must affect future notifications.

It must not rewrite historical notification records.

---

# 138. Contract for Historical Data

Historical event records should remain readable even if:

```text
topic disabled
AI profile deleted
provider disconnected
```

References should be retained or represented as historical/deleted metadata.

---

# 139. Contract for Deleted Configuration

If a referenced AI profile is deleted:

```text
Historical analysis
```

must still show the profile/version metadata that was used.

---

# 140. Contract for Provider Unavailability

Provider outage must not cause data loss.

The system should prefer:

```text
Store
Retry
Recover
```

over:

```text
Drop
```

---

# 141. Contract for AI Cost Limits

AI requests may be blocked when configured limits are reached.

The result should be explicit:

```text
AI_SKIPPED_COST_LIMIT
```

or an equivalent status.

The event remains available.

---

# 142. Contract for Content Generation

Content generation must be downstream from intelligence processing.

It must not block:

```text
Gmail monitoring
Event storage
AI summary
Desktop notifications
```

---

# 143. Contract for Long-Running Content Jobs

Content generation should be represented as a job:

```text
QUEUED
PROCESSING
REVIEW_REQUIRED
APPROVED
PUBLISHING
PUBLISHED
FAILED
```

---

# 144. Contract for Human Approval

Publishing must require:

```text
Approved
```

unless the user explicitly configures an automated publishing workflow in a future version.

---

# 145. Contract for External Publishing

The publisher receives an approved content object.

It must not directly inspect:

```text
Gmail
Topic
Raw event database
```

---

# 146. Contract for Backward Compatibility

When extending a contract:

Prefer:

```text
Optional new field
```

over:

```text
Breaking required field
```

where semantically safe.

---

# 147. Contract Change Procedure

Before changing a contract:

```text
1. Search all implementations.
2. Search all consumers.
3. Update documentation.
4. Update tests.
5. Update implementations.
6. Run architecture tests.
7. Run integration tests.
```

---

# 148. AI Coding Agent Contract Rules

AI coding agents must:

```text
Read this document before changing interfaces.
```

They must not:

```text
Invent method signatures
Duplicate interfaces
Bypass ports
Expose SDK types
Return inconsistent error types
Modify contracts without updating documentation
```

---

# 149. AI Agent Interface Search Rule

Before creating:

```text
IWhatever
```

the agent must search for an existing contract that already expresses the required capability.

---

# 150. AI Agent Provider Rule

A new provider must implement an existing provider contract where possible.

Do not create:

```text
BedrockService
OpenAIService
GeminiService
```

with unrelated APIs if the common capability is:

```text
AIProvider
```

---

# 151. AI Agent UI Rule

UI components must consume:

```text
DTO/ViewModel
```

rather than:

```text
Database Model
Gmail Model
Bedrock Response
```

---

# 152. AI Agent Persistence Rule

Application code must use:

```text
Repository
```

rather than:

```text
sqlite3
SQLAlchemy session
raw SQL
```

directly.

---

# 153. AI Agent Async Rule

The agent must not introduce:

```text
time.sleep()
```

or blocking network calls into the GUI thread.

---

# 154. AI Agent Testing Rule

Every contract implementation should have tests proving:

```text
Happy path
Validation
Failure behavior
Retry behavior where applicable
Idempotency where applicable
```

---

# 155. Contract Matrix

| Boundary | Contract | Implementation |
|---|---|---|
| Gmail → Application | SourceProvider | Gmail adapter |
| Pub/Sub → Application | PubSub adapter | Google Pub/Sub |
| Application → AI | AIProvider | Bedrock initially |
| Application → DB | Repository | SQLite |
| Application → Notifications | NotificationProvider | Windows |
| Application → Storage | AttachmentStorage | Local filesystem |
| Application → Secrets | SecretStore | Windows credential store |
| Application → Time | Clock | System clock |
| Application → UI | DTO/ViewModel | PySide6 |
| Application → Content | ScriptGenerator/Publisher | Future |
| Application → Metrics | Metrics boundary | Future |

---

# 156. Core Processing Contract

The complete event flow is:

```text
Gmail
  |
  v
Pub/Sub
  |
  v
Gmail Adapter
  |
  v
NormalizedSourceEvent
  |
  v
ProcessIntelligenceEvent
  |
  +--> Deduplication
  |
  +--> Topic Resolution
  |
  +--> Event Persistence
  |
  +--> AI Provider
  |
  +--> AI Validation
  |
  +--> Priority Engine
  |
  +--> Notification Policy
  |
  +--> Notification Queue
  |
  +--> Domain Events
  |
  v
Completed Intelligence Event
```

---

# 157. Real-Time UI Contract

The real-time UI flow is:

```text
Gmail Event
    |
    v
Application Processing
    |
    v
Internal Event
    |
    v
ViewModel
    |
    +--> Live Feed
    |
    +--> Notification Center
    |
    +--> Desktop Popup
```

The UI never needs to poll Gmail.

---

# 158. Five-Second Intelligence Contract

The dashboard/popup must be able to display:

```text
Topic
Priority
Headline
Short AI summary
Time
```

without requiring a source API call.

This data should already exist in the event/analysis model.

---

# 159. Source Investigation Contract

When the user chooses:

```text
Open Source
```

the application resolves:

```text
SourceReference
```

which may contain:

```text
provider
external_id
url
thread_id
```

The UI then opens the source through the appropriate mechanism.

---

# 160. Final Contract Principles

The contracts in this document establish the following rules:

```text
External providers are replaceable.
AI is replaceable.
Database is replaceable.
Notifications are replaceable.
UI is replaceable in principle.
Business rules remain independent.
Events are traceable.
Operations are idempotent where required.
Failures are explicit.
Long-running work is asynchronous.
Historical data remains valuable.
AI output is validated.
User-configured topics are data-driven.
```

---

# 161. Final Architecture Contract

The most important boundary is:

```text
               +----------------------+
               |      PRESENTATION    |
               +----------+-----------+
                          |
                          | DTOs / Commands / Queries
                          v
               +----------------------+
               |     APPLICATION      |
               +----------+-----------+
                          |
                          | Domain objects / ports
                          v
               +----------------------+
               |        DOMAIN        |
               +----------+-----------+
                          ^
                          |
                    Interfaces
                          |
               +----------+-----------+
               |    INFRASTRUCTURE    |
               +----------------------+
                 |      |       |
               Gmail    AI     SQLite
```

The dependency direction must remain inward.

---

# 162. Final Implementation Rule

A component may change its internal implementation freely if:

```text
Input contract remains valid
Output contract remains valid
Error semantics remain compatible
Side effects remain documented
Idempotency remains valid
Security assumptions remain valid
```

This allows the project to evolve without forcing every other component to change.

---

# 163. Contract Completion Criteria

This document is considered sufficiently implemented when:

```text
[ ] Core domain entities have defined contracts
[ ] SourceProvider exists
[ ] Gmail adapter implements SourceProvider
[ ] AIProvider exists
[ ] Bedrock adapter implements AIProvider
[ ] NotificationProvider exists
[ ] Windows notification adapter implements it
[ ] Repository contracts exist
[ ] SQLite implementations exist
[ ] UnitOfWork exists
[ ] Processing state contract exists
[ ] Internal event contracts exist
[ ] UI DTOs exist
[ ] Application commands/queries exist
[ ] Error hierarchy exists
[ ] Retry behavior is defined
[ ] Idempotency is tested
[ ] Contract tests exist
```

---

# 164. Final Principle

> **Contracts are the seams that allow InsightFlow AI to grow without becoming tightly coupled.**

The implementation should therefore optimize for:

```text
Clear contracts
+
Small interfaces
+
Explicit data models
+
Stable boundaries
+
Testability
+
Replaceability
```

rather than exposing internal implementation details between modules.

This contract-first approach is especially important because the project will be developed with AI coding agents. The contracts provide the guardrails that allow those agents to implement individual components without accidentally redesigning the entire system.
