# InsightFlow AI — System Design

**Document:** `05_System_Design.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent:** `04_System_Architecture.md`

---

# 1. Purpose

This document translates the high-level architecture into an implementable system design.

It defines:

- Module boundaries.
- Responsibilities.
- Interfaces.
- Core domain objects.
- Processing state machine.
- Main sequence flows.
- Dependency injection.
- Background processing.
- Error and retry behavior.
- Repository contracts.
- Provider contracts.
- Project structure.
- Component interaction rules.

This document is intended to be directly usable by developers and AI coding agents such as Cursor, Codex, Claude Code, and Gemini.

---

# 2. Design Approach

The implementation will use:

```text
Clean Architecture
+
DDD-inspired domain modeling
+
Ports and Adapters
+
Modular Monolith
+
Event-driven processing
+
Dependency Injection
```

The initial application is a Windows desktop application, but the core business logic must remain platform-independent.

---

# 3. Logical Layers

```text
+-------------------------------------------------------+
| Presentation                                         |
| PySide6 UI / Tray / Notification                     |
+----------------------------+--------------------------+
                             |
                             v
+-------------------------------------------------------+
| Application                                           |
| Use Cases / Commands / Queries / Orchestration       |
+----------------------------+--------------------------+
                             |
                             v
+-------------------------------------------------------+
| Domain                                               |
| Entities / Value Objects / Policies / Interfaces     |
+----------------------------+--------------------------+
                             ^
                             |
+-------------------------------------------------------+
| Infrastructure                                       |
| Gmail / PubSub / Bedrock / SQLite / Windows / Files |
+-------------------------------------------------------+
```

Dependency rule:

```text
Presentation -> Application -> Domain

Infrastructure -> Application/Domain interfaces

Domain -> No infrastructure
```

---

# 4. Proposed Project Structure

The initial source tree should be:

```text
src/
└── insightflow/
    ├── __init__.py
    ├── main.py
    │
    ├── domain/
    │   ├── __init__.py
    │   ├── entities/
    │   ├── value_objects/
    │   ├── enums/
    │   ├── events/
    │   ├── policies/
    │   ├── services/
    │   └── ports/
    │
    ├── application/
    │   ├── __init__.py
    │   ├── commands/
    │   ├── queries/
    │   ├── services/
    │   ├── handlers/
    │   ├── dto/
    │   └── workflows/
    │
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── gmail/
    │   ├── pubsub/
    │   ├── ai/
    │   ├── persistence/
    │   ├── notifications/
    │   ├── attachments/
    │   ├── storage/
    │   ├── security/
    │   └── logging/
    │
    ├── presentation/
    │   ├── __init__.py
    │   ├── ui/
    │   ├── viewmodels/
    │   ├── notifications/
    │   ├── tray/
    │   └── controllers/
    │
    └── shared/
        ├── config/
        ├── exceptions/
        ├── result/
        ├── clock/
        └── utilities/
```

Tests:

```text
tests/
├── unit/
│   ├── domain/
│   └── application/
├── integration/
│   ├── gmail/
│   ├── ai/
│   └── persistence/
├── e2e/
└── fixtures/
```

Documentation:

```text
docs/
├── ADR/
├── diagrams/
└── ...
```

---

# 5. Domain Model

The first major domain concepts are:

```text
Source
Topic
AIProfile
IntelligenceEvent
ProcessingRecord
AIAnalysis
Notification
Attachment
Story
Rule
Workflow
ContentJob
```

---

# 6. Source Entity

A `Source` represents an external information provider.

Example:

```text
Source
-------------------------
id
name
type
status
configuration_reference
created_at
updated_at
enabled
```

Examples:

```text
Gmail
RSS
YouTube
News API
```

A source does not contain topic-specific behavior.

---

# 7. Topic Entity

A `Topic` represents the user's monitoring intent.

Example:

```text
Topic
-------------------------
id
name
description
source_id
source_identifier
ai_profile_id
priority_policy
notification_policy
attachment_policy
content_policy
enabled
created_at
updated_at
```

Example:

```text
TRUMP
    source = Gmail
    label = TRUMP
    profile = Trading / Geopolitics
```

Another:

```text
CELEBRITY_X
    source = Gmail
    label = CELEBRITY_X
    profile = Entertainment
```

No code changes are required when a new topic is added.

---

# 8. AI Profile

An AI profile defines analysis behavior.

```text
AIProfile
-------------------------
id
name
description
system_prompt
output_schema
version
enabled
created_at
updated_at
```

Example:

```text
Trading / Geopolitics
Entertainment
Technology
General News
```

---

# 9. Intelligence Event

`IntelligenceEvent` is the central normalized information object.

Conceptual fields:

```text
IntelligenceEvent
-------------------------
id
source_id
external_id
topic_id
occurred_at
received_at
title
author
content
source_url
metadata
content_hash
status
```

It must not contain Gmail-specific types.

---

# 10. Processing Record

A processing record tracks the lifecycle of an event.

```text
ProcessingRecord
-------------------------
id
event_id
status
attempt_count
started_at
completed_at
last_error
correlation_id
```

This supports recovery and auditing.

---

# 11. AI Analysis

```text
AIAnalysis
-------------------------
id
event_id
provider
model
profile_id
profile_version
summary
headline
facts
entities
importance
priority
confidence
uncertainty
topic_analysis
market_impact
follow_up
created_at
```

Structured fields may be represented using normalized relational data or JSON depending on the final database design.

---

# 12. Notification

```text
Notification
-------------------------
id
event_id
topic_id
priority
title
summary
status
created_at
displayed_at
dismissed_at
opened_at
```

Possible statuses:

```text
PENDING
DISPLAYED
DISMISSED
OPENED
SUPPRESSED
FAILED
```

---

# 13. Attachment

```text
Attachment
-------------------------
id
event_id
external_id
filename
mime_type
size
download_status
processing_status
storage_reference
content_hash
created_at
```

---

# 14. Story

A story groups related events.

```text
Story
-------------------------
id
topic_id
title
summary
status
first_event_at
last_event_at
created_at
updated_at
```

Events may later reference a story.

Story grouping is not required for the first MVP but the model should accommodate it.

---

# 15. Rule

A rule represents conditional behavior.

Conceptually:

```text
Rule
-------------------------
id
name
enabled
conditions
actions
priority
created_at
updated_at
```

Example:

```text
IF topic = TRUMP
AND priority >= HIGH
THEN notify
```

---

# 16. Content Job

Future YouTube/content generation is represented independently.

```text
ContentJob
-------------------------
id
event_id / story_id
type
status
target_duration
script
metadata
created_at
updated_at
```

Possible statuses:

```text
PENDING
GENERATING
REVIEW
APPROVED
REJECTED
PUBLISHED
FAILED
```

---

# 17. Domain Value Objects

Value objects should be used for concepts with validation and semantic meaning.

Examples:

```text
EventId
TopicId
SourceId
Priority
Confidence
ProcessingStatus
NotificationStatus
AIProviderId
ModelId
EmailAddress
MimeType
```

A raw string should not be used everywhere when a concept has meaningful validation.

---

# 18. Domain Enumerations

Initial enums:

```text
Priority
    LOW
    MEDIUM
    HIGH
    CRITICAL

ProcessingStatus
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

---

# 19. Ports / Interfaces

Interfaces belong in inner layers.

Examples:

```text
SourceProvider
AIProvider
EventRepository
TopicRepository
AIProfileRepository
NotificationProvider
AttachmentStorage
AttachmentProcessor
Clock
UnitOfWork
```

Infrastructure implements these interfaces.

---

# 20. SourceProvider Interface

Conceptual contract:

```python
class SourceProvider(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health(self) -> SourceHealth: ...
    def subscribe(self, configuration: SourceConfiguration) -> None: ...
    def retrieve_event(self, external_id: str) -> RawSourceEvent: ...
```

The exact interface may evolve during implementation.

---

# 21. AIProvider Interface

Conceptual contract:

```python
class AIProvider(Protocol):
    def analyze(
        self,
        request: AIRequest,
    ) -> AIResponse:
        ...
```

The application must not depend on `boto3` or another AI SDK.

---

# 22. Repository Interfaces

Examples:

```python
class EventRepository(Protocol):
    def get_by_id(self, event_id: EventId) -> IntelligenceEvent | None: ...
    def get_by_external_id(self, source_id, external_id): ...
    def save(self, event): ...
```

Other repositories:

```text
TopicRepository
SourceRepository
AIProfileRepository
ProcessingRepository
NotificationRepository
AttachmentRepository
StoryRepository
RuleRepository
ContentJobRepository
```

---

# 23. Unit of Work

Related database operations should be coordinated through a unit-of-work abstraction.

Example:

```text
Create Event
+
Create Processing Record
+
Save Metadata
```

must be able to commit atomically when required.

---

# 24. Application Use Cases

Initial use cases:

```text
ConnectGmail
DisconnectGmail
RefreshGmailLabels

CreateTopic
UpdateTopic
DisableTopic
DeleteTopic

StartMonitoring
PauseMonitoring
ResumeMonitoring

HandleExternalEvent
ProcessIntelligenceEvent
RetryProcessing

GenerateAIAnalysis

CreateNotification
DismissNotification
OpenNotification

SearchEvents
GetEventDetails

DownloadAttachment
ProcessAttachment
```

Future:

```text
CreateStory
UpdateStory
GenerateYouTubeScript
GenerateVideo
ApproveContent
PublishYouTube
```

---

# 25. Use Case Design

Each use case should have a narrow responsibility.

Example:

```text
ProcessIntelligenceEvent
```

should coordinate processing.

It should not contain:

- SQL queries.
- Gmail SDK calls.
- PySide6 code.
- Bedrock SDK calls.

Instead it depends on abstractions.

---

# 26. Main Event Processing Sequence

```text
External Event
      |
      v
Event Receiver
      |
      v
HandleExternalEvent
      |
      v
Retrieve Source Event
      |
      v
Normalize
      |
      v
Resolve Topic
      |
      v
Check Duplicate
      |
      v
Create Processing Record
      |
      v
Generate AI Analysis
      |
      v
Validate AI Output
      |
      v
Calculate Priority
      |
      v
Persist
      |
      v
Notification Policy
      |
      v
Notification Queue
      |
      v
Complete
```

---

# 27. Gmail Event Sequence

```text
Gmail
  |
  | mailbox change
  v
Google Cloud Pub/Sub
  |
  v
PubSubReceiver
  |
  v
GmailEventResolver
  |
  v
GmailClient
  |
  v
GmailMessage
  |
  v
GmailNormalizer
  |
  v
IntelligenceEvent
```

---

# 28. Gmail Watch Lifecycle

Gmail watch subscriptions may expire and must be renewed.

The system should include a dedicated lifecycle component:

```text
GmailWatchManager
```

Responsibilities:

- Create watch.
- Track expiration.
- Renew before expiration.
- Detect failure.
- Re-establish watch.
- Report status.

The exact renewal interval should be determined from current Gmail API behavior and documented in the implementation/ADR.

---

# 29. Pub/Sub Receiver

The Pub/Sub receiver should:

1. Receive notification.
2. Validate message structure.
3. Extract Gmail mailbox/change information.
4. Acknowledge appropriately.
5. Trigger asynchronous processing.
6. Avoid doing expensive AI processing inside the receiver itself.

The receiver must remain lightweight.

---

# 30. Acknowledgement Strategy

The Pub/Sub acknowledgement strategy must prevent both:

```text
Premature acknowledgement
```

and:

```text
Unnecessary duplicate delivery
```

The detailed acknowledgement policy will be finalized during Gmail integration testing.

---

# 31. Event Processing Worker

A background worker receives internal processing jobs.

Conceptually:

```text
Pub/Sub
   |
   v
Event Queue
   |
   v
Processing Worker Pool
   |
   +--> Event A
   +--> Event B
   +--> Event C
```

Worker concurrency must be bounded.

---

# 32. AI Worker

AI processing should occur outside the GUI thread.

```text
Processing Worker
      |
      v
AIRequest
      |
      v
AIProvider
      |
      v
AIResponse
      |
      v
Schema Validation
```

---

# 33. Notification Worker

Notification display should also be decoupled.

```text
Application
    |
    v
NotificationQueue
    |
    v
WindowsNotificationProvider
    |
    v
Popup
```

The notification provider should not know how AI processing works.

---

# 34. Threading Model

Recommended conceptual model:

```text
GUI Thread
    |
    +--> UI events/signals only
    |
Background Task Manager
    |
    +--> Gmail/API tasks
    +--> AI tasks
    +--> Attachment tasks
    +--> Persistence tasks
```

The exact Python mechanism may use:

```text
asyncio
QThread
QThreadPool
concurrent.futures
```

or a combination.

The implementation should select the simplest safe mechanism rather than mixing concurrency frameworks unnecessarily.

---

# 35. Concurrency Rule

The project must have one clearly defined concurrency strategy.

AI agents must not independently introduce different worker systems into different modules.

A new background mechanism requires architectural review.

---

# 36. Processing Queue

The application should have a logical internal queue for processing events.

Queue item:

```text
ProcessingJob
-------------------------
job_id
event_id
priority
attempt
created_at
scheduled_at
```

Priority may influence processing order.

---

# 37. Retry Design

A retryable operation should follow:

```text
Failure
  |
  v
Classify Error
  |
  +---- Non-retryable ---> FAILED
  |
  +---- Retryable
          |
          v
     Retry Policy
          |
          v
     Retry Pending
          |
          v
      Worker Queue
```

Retry metadata should include:

```text
attempt_count
last_error
next_retry_at
```

---

# 38. Retry Policy

Initial recommended retry behavior:

```text
Attempt 1 -> immediate/short delay
Attempt 2 -> exponential delay
Attempt 3 -> longer delay
Final     -> FAILED
```

Exact timings should be configurable centrally.

---

# 39. Error Classification

Errors should be classified into:

```text
Transient
Permanent
Authentication
Authorization
Validation
RateLimit
Network
Provider
Database
Application
Unknown
```

This determines whether retry is appropriate.

---

# 40. Idempotency

Before processing an external event:

```text
source_id + external_id
```

should be checked.

If already successfully processed:

```text
Return existing result
```

rather than reprocessing.

---

# 41. Content Hash

A normalized content hash should be generated where practical.

Example:

```text
SHA-256(normalized content)
```

This supports duplicate detection.

---

# 42. Topic Resolution

Topic resolution should be a dedicated service.

Conceptually:

```text
IntelligenceEvent
      |
      v
TopicResolver
      |
      +--> Topic
      |
      +--> No matching topic
```

For Gmail, the initial resolver may use the configured Gmail label.

Future sources may use:

- Source configuration.
- Rules.
- User-defined matching.
- AI classification.

---

# 43. AI Prompt Construction

The prompt builder should combine:

```text
System Instructions
+
AI Profile
+
Source Content
+
Topic Context
+
Output Schema
```

Conceptually:

```text
PromptBuilder
      |
      v
AIRequest
```

Prompt construction must be testable independently from the AI provider.

---

# 44. AI Request

A provider-independent request may contain:

```text
AIRequest
-------------------------
profile
profile_version
system_instruction
user_content
output_schema
temperature
max_tokens
metadata
```

Provider-specific conversion occurs in the adapter.

---

# 45. AI Response

A provider-independent response may contain:

```text
AIResponse
-------------------------
content
structured_data
provider
model
usage
latency
raw_reference
```

Raw provider-specific response objects should not escape the infrastructure adapter.

---

# 46. AI Output Validation

The validation pipeline:

```text
AI Response
     |
     v
Parse
     |
     v
Schema Validation
     |
     +---- Valid
     |       |
     |       v
     |    AIAnalysis
     |
     +---- Invalid
             |
             v
        Recovery/Retry
```

---

# 47. AI Hallucination Boundary

The system should represent:

```text
source_facts
ai_interpretation
uncertainties
```

separately where practical.

For example:

```text
Confirmed:
Trump issued a statement.

AI Interpretation:
The statement may increase geopolitical uncertainty.

Uncertainty:
Actual policy implementation is not confirmed.
```

---

# 48. Priority Calculation

Priority calculation should occur after AI analysis where AI priority is part of the profile.

```text
Topic Policy
     +
AI Analysis
     +
Rules
     |
     v
PriorityEngine
     |
     v
Priority
```

---

# 49. Notification Policy

Notification policy decides whether an event should interrupt the user.

Example:

```text
IF priority >= HIGH
AND notifications enabled
AND not in quiet hours
THEN show notification
```

This logic belongs in an application/domain policy, not in the UI.

---

# 50. Notification Presentation Model

The UI should receive a presentation-friendly model:

```text
NotificationViewModel
-------------------------
title
topic
priority
summary
impact
timestamp
actions
```

The UI should not receive a raw `AIAnalysis` and decide how to interpret it.

---

# 51. Notification Animation

The presentation layer owns:

- Position.
- Animation.
- Fade.
- Duration.
- Stacking.
- Theme.
- User interaction.

The application layer owns:

- Whether notification should exist.
- Notification priority.
- Notification content.

---

# 52. Search Design

Search requests should pass through:

```text
SearchQuery
     |
     v
SearchService
     |
     v
EventRepository
     |
     v
SearchResult
```

The UI must not construct SQL.

---

# 53. Search Result

A result should contain enough information for a list view:

```text
EventId
Topic
Headline
Summary
Priority
Timestamp
Source
```

Detailed data is loaded only when required.

---

# 54. Database Transactions

Transactions should be used for operations that must remain consistent.

Example:

```text
Save Event
+
Save Processing Record
+
Save AI Analysis
```

The database should not expose half-completed processing state as completed.

---

# 55. Repository Responsibility

Repositories are responsible for:

- Persistence.
- Retrieval.
- Querying.
- Mapping persistence models.

Repositories are not responsible for:

- AI.
- Notifications.
- Gmail.
- UI.
- Business workflows.

---

# 56. Persistence Mapping

The domain model should not be the database ORM model.

Recommended:

```text
Domain Entity
      ^
      |
Mapper
      |
      v
Persistence Model
```

This reduces coupling between the domain and database technology.

---

# 57. Configuration Management

Configuration should have layers:

```text
Default Configuration
        |
        v
User Configuration
        |
        v
Environment Configuration
        |
        v
Runtime Configuration
```

Secrets are handled separately.

---

# 58. Dependency Injection Composition Root

Dependencies should be assembled in one place.

Example:

```text
main.py
   |
   v
ApplicationContainer
   |
   +--> GmailProvider
   +--> BedrockProvider
   +--> SQLiteRepositories
   +--> NotificationProvider
   +--> ProcessingService
```

Business classes should receive dependencies rather than constructing them.

---

# 59. Composition Root Rule

Only the composition root should decide concrete implementations.

For example:

```text
AIProvider = BedrockAIProvider
```

should be selected in configuration/composition code.

Not inside:

```text
AIAnalysisService
```

---

# 60. Domain Services

A domain service should exist only when behavior does not naturally belong to one entity.

Potential examples:

```text
PriorityPolicy
DeduplicationPolicy
NotificationPolicy
TopicMatchingPolicy
```

Do not create a service merely to wrap one line of code.

---

# 61. Application Services

Application services coordinate workflows.

Example:

```text
ProcessIntelligenceEventService
```

may orchestrate:

```text
EventRepository
TopicResolver
DeduplicationService
AIProvider
PriorityEngine
NotificationPolicy
UnitOfWork
```

It should remain orchestration-focused.

---

# 62. Avoid God Services

The project must not create a class such as:

```text
InsightFlowManager
```

that performs:

- Gmail access.
- AI calls.
- SQL.
- UI.
- Notifications.
- Attachment processing.

Responsibilities must remain separated.

---

# 63. Presentation/ViewModel Boundary

UI widgets should communicate through view models/controllers.

Example:

```text
TopicPage
    |
    v
TopicViewModel
    |
    v
TopicApplicationService
```

The widget does not directly manipulate domain entities in complex ways.

---

# 64. UI State

UI state should be represented explicitly.

Example:

```text
ConnectionState
MonitoringState
ProcessingState
NotificationState
```

This prevents widgets from independently inventing status logic.

---

# 65. Event Bus Design

Internal events may include:

```text
SourceEventReceived
IntelligenceEventCreated
ProcessingStarted
AIAnalysisCompleted
ProcessingCompleted
NotificationRequested
NotificationDisplayed
ProcessingFailed
```

Handlers should be registered through the application composition layer.

---

# 66. Event Bus Rule

The event bus should not replace ordinary method calls.

Use direct method calls for synchronous request/response behavior.

Use events for:

- Decoupled notifications.
- Asynchronous reactions.
- Cross-module events.

---

# 67. Story Grouping Design

Future story grouping should use:

```text
StoryMatcher
```

Input:

```text
New IntelligenceEvent
Existing Stories
```

Output:

```text
Existing Story
OR
New Story
```

The initial implementation may use simple deterministic matching before semantic AI matching is introduced.

---

# 68. Content Generation Design

Content generation should use:

```text
ContentService
```

with providers:

```text
ScriptGenerator
VoiceGenerator
ImageGenerator
VideoGenerator
ThumbnailGenerator
Publisher
```

Each provider must be replaceable.

---

# 69. Future YouTube Script Flow

```text
Story/Event
    |
    v
ContentRequest
    |
    v
ScriptGenerator
    |
    v
Draft Script
    |
    v
User Review
    |
    +---- Edit
    |
    +---- Regenerate
    |
    +---- Approve
```

---

# 70. Security Boundary

Security-sensitive operations should be isolated behind interfaces.

Example:

```text
SecretStore
TokenStore
OAuthManager
```

The rest of the application should not know how Windows credentials are stored.

---

# 71. Clock Abstraction

Time-dependent logic should use a `Clock` abstraction.

Instead of:

```python
datetime.now()
```

throughout business logic, use:

```text
Clock.now()
```

This makes tests deterministic.

---

# 72. External URL Handling

Opening Gmail URLs or future web links should pass through a dedicated presentation/application action.

External content must not be blindly executed.

---

# 73. Logging Boundary

Application/domain operations may emit structured logging events through an abstraction.

Infrastructure determines how logs are written.

Business logic must not depend directly on a logging framework.

---

# 74. Metrics Boundary

Metrics should be collected through an abstraction where practical.

Example:

```text
Metrics.increment("events.received")
Metrics.observe("ai.latency", duration)
```

The initial implementation may use local metrics.

---

# 75. Configuration Validation

Startup should validate:

```text
Database configuration
AI configuration
Gmail configuration
Notification configuration
Storage paths
```

Invalid optional features should disable only those features where possible.

---

# 76. Failure Scenarios

## Scenario A — Gmail unavailable

```text
Gmail failure
   |
   v
Retry
   |
   v
Status = Reconnecting
   |
   v
Successful connection
   |
   v
Resume monitoring
```

---

## Scenario B — AI unavailable

```text
Event retrieved
   |
   v
AI unavailable
   |
   v
Event stored
   |
   v
RETRY_PENDING
   |
   v
AI recovers
   |
   v
Process event
```

---

## Scenario C — Notification failure

```text
AI complete
   |
   v
Persist result
   |
   v
Notification fails
   |
   v
Result remains completed
Notification = FAILED
```

The intelligence must not be lost because the notification failed.

---

## Scenario D — Application crashes during AI processing

On restart:

```text
AI_PROCESSING
      |
      v
Recovery Scan
      |
      v
RETRY_PENDING
      |
      v
Process again
```

---

# 77. Data Flow

The main data flow is:

```text
External Source
      |
      v
Raw Event
      |
      v
Normalized Event
      |
      v
Topic
      |
      v
AI Request
      |
      v
AI Analysis
      |
      v
Priority
      |
      v
Persisted Intelligence
      |
      +----> Notification
      |
      +----> Search
      |
      +----> Story
      |
      +----> Content Workflow
```

---

# 78. Dependency Graph

Conceptual dependency graph:

```text
Presentation
     |
     v
Application
     |
     v
Domain
     ^
     |
Infrastructure
```

Infrastructure implementations depend on domain/application interfaces.

No dependency should point:

```text
Domain -> Infrastructure
Domain -> Presentation
```

---

# 79. Module Dependency Rules

Allowed:

```text
presentation -> application
application -> domain
infrastructure -> application/domain
shared -> domain-safe utilities
```

Not allowed:

```text
domain -> infrastructure
domain -> presentation
application -> PySide6
application -> boto3
application -> Gmail SDK
presentation -> SQLAlchemy
presentation -> Gmail SDK
```

---

# 80. Interface Naming

Interfaces should use capability-oriented names.

Prefer:

```text
AIProvider
SourceProvider
NotificationProvider
EventRepository
```

Avoid vague interfaces:

```text
Manager
Helper
Utility
CommonService
```

unless the name has a precise responsibility.

---

# 81. Exception Handling

Exceptions should be handled at appropriate boundaries.

Infrastructure exceptions should be translated into meaningful application exceptions.

Example:

```text
Google API exception
      |
      v
GmailProviderError
      |
      v
Application handling
```

The raw provider exception should not leak through the entire application.

---

# 82. Domain Exceptions

Examples:

```text
TopicNotFound
InvalidPriority
InvalidProcessingTransition
DuplicateEvent
InvalidAIAnalysis
InvalidConfiguration
```

---

# 83. Result Handling

For expected business failures, the application may use a typed result pattern instead of exceptions everywhere.

Conceptually:

```text
Result
    Success(value)
    Failure(error)
```

Exceptions remain appropriate for unexpected/system failures.

The exact approach should be standardized in the coding guide.

---

# 84. Database Migration Strategy

Database schema changes must use versioned migrations.

Example:

```text
migration_001_initial
migration_002_add_ai_profile_version
migration_003_add_story
```

Migrations must not be manually edited after release unless a documented migration strategy is used.

---

# 85. Application Version

The application should expose:

```text
Application Version
Database Schema Version
```

This helps support upgrades and troubleshooting.

---

# 86. Configuration Version

Configuration schemas should also be versioned where necessary.

A future application version must be able to migrate older configuration safely.

---

# 87. Testing Boundaries

## Domain Tests

Test:

```text
Priority
State transitions
Policies
Value objects
Deduplication rules
```

## Application Tests

Test:

```text
Use cases
Orchestration
Retry decisions
Notification policies
Topic resolution
```

## Infrastructure Tests

Test:

```text
Gmail adapter
AI provider
Database
Notifications
```

## E2E Tests

Test:

```text
Gmail event -> AI -> notification
```

where practical.

---

# 88. Test Fixture Strategy

Tests should use deterministic fixtures for:

```text
Gmail messages
AI responses
AI failures
Duplicate messages
Attachments
Configuration
```

Real credentials must never be embedded in test fixtures.

---

# 89. AI Regression Testing

Prompt changes can change output.

Therefore:

```text
Prompt Version
      |
      v
Regression Fixture
      |
      v
Schema + Semantic Checks
```

Exact wording should not normally be required to remain identical.

---

# 90. Initial Implementation Order

Recommended implementation sequence:

```text
1. Project skeleton
2. Configuration
3. Domain entities/value objects
4. Repository interfaces
5. SQLite persistence
6. Gmail OAuth
7. Gmail label discovery
8. Gmail watch/PubSub
9. Event normalization
10. Processing state machine
11. AI provider abstraction
12. Bedrock implementation
13. AI output validation
14. Notification abstraction
15. Windows popup
16. System tray
17. Retry/recovery
18. History/search
19. Attachment support
20. Hardening/testing
```

Do not implement YouTube automation before the core intelligence pipeline is stable.

---

# 91. First Vertical Slice

The first implementation milestone should be a complete vertical slice rather than building every layer independently.

Target:

```text
Gmail
  |
  v
New labeled email
  |
  v
Normalized Event
  |
  v
AI Summary
  |
  v
SQLite
  |
  v
Windows Popup
```

Once this works reliably, expand each subsystem.

---

# 92. Recommended First Demo

The first successful demonstration should be:

1. Start InsightFlow.
2. Gmail shows `Connected`.
3. Topic `TRUMP` is enabled.
4. Send/create a test email with the `TRUMP` label.
5. Gmail push event reaches the application.
6. Application retrieves the email.
7. AI produces a summary.
8. Summary is stored.
9. Bottom-right popup appears.
10. Clicking the popup opens the details/source.
11. Application remains running in the system tray.

This is the first meaningful end-to-end proof of architecture.

---

# 93. Architecture Review Gate

Before adding advanced functionality, verify:

```text
[ ] Domain has no infrastructure dependency
[ ] UI has no business logic
[ ] AI provider is replaceable
[ ] Gmail provider is replaceable
[ ] Database is accessed through repositories
[ ] Background work does not block UI
[ ] Processing is idempotent
[ ] Retry is centralized
[ ] Errors are observable
[ ] Configuration is centralized
[ ] Tests cover core logic
```

---

# 94. AI Coding Agent Rules

Any AI agent modifying this project must:

1. Read `00_Project_Vision.md`.
2. Read `01_Product_Requirements.md`.
3. Read `02_Functional_Requirements.md`.
4. Read `03_Non_Functional_Requirements.md`.
5. Read `04_System_Architecture.md`.
6. Read this document.
7. Identify affected layers before coding.
8. Reuse existing interfaces.
9. Avoid bypassing architectural boundaries.
10. Add/update tests.
11. Update documentation when behavior changes.
12. Explain architectural impact when proposing a significant change.

A coding agent must not create an alternative architecture simply because it is easier to implement.

---

# 95. Design Review Questions

Before accepting a new component, ask:

```text
What responsibility does it own?

Which layer does it belong to?

What does it depend on?

Can it be unit tested?

Does it know about external infrastructure?

Can it be replaced?

Does it violate SRP?

Does it introduce duplicate logic?

Does it make the UI responsible for business behavior?

Does it create a new concurrency mechanism?
```

---

# 96. Anti-Patterns Prohibited

The following patterns are prohibited without explicit architectural approval:

```text
God classes
Global mutable state
Service locator everywhere
Direct SQL in UI
Direct SDK calls in UI
Hardcoded prompts
Hardcoded topics
Hardcoded provider selection
Infinite retry loops
Blocking GUI thread
Unbounded worker creation
Silent exception swallowing
Duplicate provider implementations
Business logic inside adapters
```

---

# 97. System Design Summary

The final initial design is:

```text
                 +-----------------------+
                 |       Gmail           |
                 +-----------+-----------+
                             |
                             v
                    Google Pub/Sub
                             |
                             v
                 +-----------------------+
                 | Event Ingestion       |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Normalization         |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Topic Resolution      |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Deduplication         |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | AI Processing         |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | AI Validation         |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Priority Engine       |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Persistence           |
                 +-----+-------------+---+
                       |             |
                       v             v
                 Notification      History
                       |
                       v
                 Windows Popup

                             |
                             v
                   Future Workflows
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
             Story AI              YouTube
                                  Content
```

---

# 98. Final Design Principle

The most important implementation rule is:

> **Build one reliable, generic intelligence pipeline and attach providers and capabilities to it through interfaces.**

The pipeline should not know whether the incoming information is:

```text
Trump
Iran
Modi
A celebrity
NIFTY
AWS
OpenAI
A company
A sports team
```

It receives an `IntelligenceEvent`, applies the configured topic/profile, generates structured intelligence, persists it, and triggers configured actions.

That is the foundation that allows InsightFlow AI to grow without becoming a collection of topic-specific scripts.
