# InsightFlow AI — System Architecture

**Document:** `04_System_Architecture.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `00_Project_Vision.md`, `01_Product_Requirements.md`, `02_Functional_Requirements.md`, `03_Non_Functional_Requirements.md`

---

# 1. Purpose

This document defines the high-level system architecture of InsightFlow AI.

The architecture is designed to support the initial use case:

```text
Google Alerts
     |
     v
Gmail Label
     |
     v
Gmail Push Notification
     |
     v
InsightFlow AI
     |
     v
AI Summary + Analysis
     |
     v
Windows Desktop Notification
```

while preserving a path toward the long-term platform:

```text
Multiple Sources
       |
       v
Common Intelligence Model
       |
       v
AI Processing
       |
       +--> Notifications
       +--> Search / History
       +--> Story Intelligence
       +--> AI Chat
       +--> YouTube Content
       +--> Publishing
```

The architecture must be generic, modular, testable, secure, and suitable for development by multiple AI coding agents.

---

# 2. Architectural Goals

The architecture shall prioritize:

1. Separation of concerns.
2. SOLID principles.
3. Dependency inversion.
4. Source independence.
5. AI-provider independence.
6. UI independence from business logic.
7. Testability.
8. Near-real-time processing.
9. Reliable event processing.
10. Idempotency.
11. Recoverability.
12. Extensibility.
13. Security.
14. Observability.
15. Controlled complexity.

---

# 3. Architectural Principles

## 3.1 Domain First

The core business/domain model must not depend on:

- Gmail SDK.
- AWS SDK.
- PySide6.
- SQLite.
- Google Cloud.
- YouTube SDK.

The domain should represent concepts such as:

```text
Topic
Source
IntelligenceEvent
AIAnalysis
Notification
Attachment
Story
Workflow
Rule
```

---

## 3.2 Dependency Direction

Dependencies should point inward.

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

More precisely:

```text
Presentation ---> Application ---> Domain

Infrastructure ---> Application
Infrastructure ---> Domain

Domain ---> Nothing external
```

The domain must remain independent of infrastructure.

---

# 4. Architectural Style

The application shall use a combination of:

```text
Clean Architecture
+
Domain-Driven Design principles
+
Hexagonal / Ports-and-Adapters principles
+
Event-driven processing
+
Plugin-oriented integrations
```

This combination is preferred because the system has many external dependencies:

```text
Gmail
Google Pub/Sub
AWS Bedrock
SQLite
Windows
Future RSS
Future YouTube
Future OpenAI
Future other providers
```

---

# 5. High-Level Architecture

```text
+---------------------------------------------------------------+
|                       Presentation Layer                      |
|                                                               |
|  PySide6 Desktop UI     System Tray     Desktop Notifications |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                     Application Layer                         |
|                                                               |
|  Use Cases   Orchestration   Commands   Queries   Workflows   |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                        Domain Layer                            |
|                                                               |
| Topics  Events  AI Analysis  Stories  Rules  Notifications    |
| Attachments  Processing State  Content Jobs                   |
+-------------------------------+-------------------------------+
                                ^
                                |
+---------------------------------------------------------------+
|                    Infrastructure Layer                       |
|                                                               |
| Gmail Adapter     Pub/Sub Adapter     AI Adapter              |
| SQLite Repository Windows Services Attachment Processors     |
| YouTube Adapter   File Storage        Logging                 |
+---------------------------------------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                       External Systems                         |
|                                                               |
| Gmail | Google Cloud Pub/Sub | AWS Bedrock | Windows | etc.   |
+---------------------------------------------------------------+
```

---

# 6. Major Components

The system is divided into the following major components:

```text
1. Presentation
2. Application Core
3. Domain
4. Source Integration
5. Event Ingestion
6. Intelligence / AI
7. Persistence
8. Notification
9. Attachment Processing
10. Workflow / Rules
11. Content Generation
12. Observability
13. Configuration
14. Security
```

---

# 7. Presentation Layer

The presentation layer is responsible only for:

- Displaying information.
- Accepting user input.
- Triggering application use cases.
- Showing application state.
- Showing errors.
- Displaying notifications.

Technology:

```text
PySide6
```

The UI must not:

- Call Gmail APIs directly.
- Call AWS Bedrock directly.
- Execute SQL directly.
- Implement business rules.
- Contain topic-specific AI prompts.
- Decide processing state transitions.

---

# 8. Application Layer

The application layer coordinates use cases.

Examples:

```text
ConnectGmail
ConfigureTopic
StartMonitoring
StopMonitoring
ProcessIncomingEvent
GenerateAISummary
ShowNotification
SearchHistory
RetryProcessing
DownloadAttachment
GenerateYouTubeScript
```

The application layer determines:

```text
What should happen?
```

The infrastructure layer determines:

```text
How an external operation is performed.
```

---

# 9. Domain Layer

The domain is the most protected layer.

Potential entities:

```text
Topic
Source
IntelligenceEvent
Story
AIAnalysis
Notification
Attachment
Workflow
Rule
ContentJob
```

Potential value objects:

```text
TopicId
SourceId
EventId
Priority
Timestamp
Confidence
ProcessingStatus
AIProviderId
ModelId
```

The domain contains business rules that do not depend on external technology.

---

# 10. Infrastructure Layer

Infrastructure implements external integrations.

Examples:

```text
GmailSourceAdapter
GooglePubSubEventReceiver
BedrockAIProvider
SQLiteEventRepository
WindowsNotificationProvider
LocalAttachmentStorage
YouTubePublisher
```

Infrastructure must implement interfaces/ports defined by inner layers.

---

# 11. Source Architecture

Sources are represented through a common abstraction.

```text
SourceProvider
      |
      +---- Gmail
      |
      +---- RSS
      |
      +---- News API
      |
      +---- YouTube
      |
      +---- Outlook
      |
      +---- Web
      |
      +---- Local Files
```

The first implementation is Gmail.

---

# 12. Source Adapter Responsibilities

A source adapter should be responsible for:

- Authentication where applicable.
- Receiving source-specific events.
- Retrieving source data.
- Translating source data into the common model.
- Returning source metadata.

It must not:

- Generate AI summaries.
- Decide notification priority.
- Render UI.
- Execute topic-specific business logic.

---

# 13. Gmail Architecture

The initial Gmail flow is:

```text
                 Google Account
                       |
                       v
                     Gmail
                       |
                 Gmail Watch
                       |
                       v
               Google Cloud Pub/Sub
                       |
                       v
             InsightFlow Event Receiver
                       |
                       v
                 Gmail API
                       |
                       v
               Gmail Message
                       |
                       v
                Normalization
```

---

# 14. Gmail Push Model

Gmail push notification should be treated as an event signal.

The notification does not replace Gmail API retrieval.

Flow:

```text
Gmail change
     |
     v
Pub/Sub notification
     |
     v
Event Receiver
     |
     v
Determine affected mailbox state
     |
     v
Gmail API
     |
     v
Retrieve relevant message(s)
```

The system must handle duplicate and out-of-order notifications.

---

# 15. Event Ingestion Layer

The ingestion layer receives external events and converts them into internal processing requests.

Conceptually:

```text
External Event
      |
      v
Event Receiver
      |
      v
Event Validator
      |
      v
Event Normalizer
      |
      v
Internal IntelligenceEvent
```

The ingestion layer must be independent from AI processing.

---

# 16. Common Intelligence Event

All future sources should produce a common internal event.

Example conceptual model:

```text
IntelligenceEvent

id
source_id
external_id
topic_id
timestamp
title
author
content
metadata
attachments
source_url
```

This allows:

```text
Gmail Event
RSS Event
Web Event
YouTube Event
```

to enter the same downstream pipeline.

---

# 17. Processing Pipeline

The core processing pipeline is:

```text
Receive
  |
  v
Validate
  |
  v
Normalize
  |
  v
Resolve Topic
  |
  v
Deduplicate
  |
  v
Classify
  |
  v
AI Process
  |
  v
Validate AI Output
  |
  v
Determine Priority
  |
  v
Persist
  |
  v
Notify
  |
  v
Trigger Optional Workflows
  |
  v
Complete
```

---

# 18. Processing State Machine

Recommended states:

```text
RECEIVED
   |
VALIDATING
   |
NORMALIZED
   |
TOPIC_RESOLVED
   |
DEDUPLICATING
   |
AI_PENDING
   |
AI_PROCESSING
   |
AI_COMPLETED
   |
PERSISTING
   |
NOTIFICATION_PENDING
   |
COMPLETED
```

Alternative states:

```text
IGNORED
DUPLICATE
RETRY_PENDING
FAILED
```

State transitions must be controlled by application/domain logic.

---

# 19. AI Architecture

AI must be exposed through an abstraction.

```text
AIProvider
    |
    +---- AWS Bedrock / Claude
    |
    +---- OpenAI
    |
    +---- Gemini
    |
    +---- Ollama
    |
    +---- Future Providers
```

The domain/application layer must not instantiate a specific AI SDK directly.

---

# 20. AI Request Flow

```text
IntelligenceEvent
       |
       v
Topic Resolver
       |
       v
AI Profile
       |
       v
Prompt Builder
       |
       v
AI Provider
       |
       v
Raw AI Response
       |
       v
Schema Validator
       |
       v
AIAnalysis
```

---

# 21. AI Profile

An AI profile defines how the AI should analyze information.

Example:

```text
Profile:
Trading / Geopolitics

Instructions:
Analyze geopolitical events for potential market implications.

Output:
Summary
Facts
Market Impact
Affected Assets
Risk
Confidence
```

Another:

```text
Profile:
Celebrity / Entertainment

Output:
Summary
Career Impact
Public Reaction
Important Follow-up
```

The profile is configuration/data, not source code.

---

# 22. AI Output Validation

AI output must be validated before it becomes trusted application data.

```text
AI Response
     |
     v
JSON/Schema Validation
     |
     +---- Valid ---> AIAnalysis
     |
     +---- Invalid -> Recovery / Retry / Failure
```

The application must not assume that AI output is always valid.

---

# 23. AI Provider Failover

Future versions may support:

```text
Primary AI Provider
        |
        v
Failure
        |
        v
Fallback Provider
```

This must be configurable and must not be introduced into the MVP unless justified.

---

# 24. Prompt Architecture

Prompts must be versioned.

Conceptually:

```text
Topic
  |
  v
AI Profile
  |
  v
Prompt Version
  |
  v
Prompt Builder
```

The processing record must retain:

```text
AI Provider
Model
Profile
Prompt Version
```

---

# 25. Deduplication Architecture

Deduplication should operate at multiple levels:

```text
Level 1:
External ID

Level 2:
Content Hash

Level 3:
Normalized Content Similarity

Level 4:
Story/Event Similarity
```

The first implementation should at least support Levels 1 and 2.

Advanced semantic story grouping can be added later.

---

# 26. Priority Engine

Priority should be determined by a dedicated component.

```text
Event
 +
Topic Configuration
 +
AI Analysis
 +
Rules
      |
      v
Priority Engine
      |
      v
LOW / MEDIUM / HIGH / CRITICAL
```

The priority engine must not be implemented inside the notification UI.

---

# 27. Notification Architecture

Notifications are provided through an abstraction.

```text
NotificationProvider
       |
       +---- Windows Desktop
       |
       +---- Future Telegram
       |
       +---- Future Email
       |
       +---- Future Slack
```

The notification system receives a domain/application notification model rather than raw Gmail data.

---

# 28. Desktop Notification Flow

```text
AIAnalysis
    |
    v
Priority Engine
    |
    v
Notification Policy
    |
    v
Notification Queue
    |
    v
Windows Notification Provider
    |
    v
Bottom-right Popup
```

The popup implementation is isolated from processing logic.

---

# 29. Notification Queue

The queue prevents notification bursts from overwhelming the user.

```text
Event A ----+
Event B ----+--> Notification Queue --> Desktop
Event C ----+
```

The queue may support:

- Priority ordering.
- Topic grouping.
- Deduplication.
- Suppression.
- Quiet hours.

---

# 30. Persistence Architecture

Persistence is accessed through repository interfaces.

Conceptually:

```text
Application
     |
     v
Repository Interface
     |
     v
SQLite Repository
```

The domain/application layers should not know SQL implementation details.

---

# 31. Database

Initial database:

```text
SQLite
```

ORM/DB technology will be finalized in the technology architecture document.

The database should store concepts such as:

```text
Sources
Topics
AI Profiles
Events
AI Analyses
Notifications
Attachments
Stories
Rules
Processing Attempts
Content Jobs
Settings
Audit Records
```

---

# 32. Future Database Scaling

SQLite is appropriate for the initial desktop application.

The architecture should allow future migration to:

```text
PostgreSQL
```

if the product evolves into a multi-user/cloud system.

The application must avoid embedding SQLite-specific assumptions into the domain layer.

---

# 33. Attachment Architecture

Attachment handling is independent of email processing.

```text
Email
  |
  v
Attachment Metadata
  |
  +--> Ignore
  |
  +--> Download
  |
  +--> Extract Content
  |
  +--> AI Processing
```

Attachment processors should use an interface.

Example:

```text
AttachmentProcessor
     |
     +---- PDF
     +---- Excel
     +---- CSV
     +---- Word
     +---- Image
```

---

# 34. Attachment Storage

Storage should be abstracted.

```text
AttachmentStorage
      |
      +---- Local Disk
      |
      +---- Future Cloud Storage
```

The domain must not assume a Windows filesystem path.

---

# 35. Workflow Architecture

The application should eventually support configurable workflows.

```text
Event
 |
 v
Condition
 |
 +---- Match ---> Action
 |
 +---- No Match -> Continue
```

Example:

```text
IF
Topic = TRUMP
AND
Priority >= HIGH

THEN
Notify
AND
Generate YouTube Script
```

The workflow engine must be independent of specific sources.

---

# 36. Content Generation Architecture

Future content generation should be a separate subsystem.

```text
Story/Event
      |
      v
Content Job
      |
      +--> Script Generator
      |
      +--> Voice Generator
      |
      +--> Image Generator
      |
      +--> Video Composer
      |
      +--> Thumbnail Generator
      |
      +--> Metadata Generator
      |
      v
Content Package
```

Each generator should have a provider abstraction.

---

# 37. YouTube Architecture

Future publishing:

```text
Content Package
      |
      v
Approval
      |
      v
YouTube Publisher
      |
      v
YouTube API
```

Automatic publishing must initially be disabled by default.

---

# 38. Application Services

Application services coordinate use cases.

Examples:

```text
MonitoringService
EventProcessingService
AIAnalysisService
NotificationService
TopicService
SearchService
AttachmentService
WorkflowService
ContentService
```

These services must remain focused and avoid becoming giant "god classes".

---

# 39. Dependency Injection

Dependencies should be injected rather than instantiated throughout business logic.

Example conceptual dependency:

```text
EventProcessingService
    |
    +--> TopicRepository
    +--> EventRepository
    +--> AIProvider
    +--> PriorityEngine
    +--> NotificationService
```

This makes the service testable.

---

# 40. Asynchronous Processing

The application contains operations that may take significant time:

```text
Network
AI
Attachment download
Attachment extraction
Database search
Content generation
```

These must execute asynchronously/background.

The UI must communicate with application services through safe signals/events/commands rather than direct blocking calls.

---

# 41. Concurrency Model

The initial desktop architecture should use controlled concurrency.

Conceptually:

```text
GUI Thread
    |
    +---- Application Commands
    |
    v
Task/Worker Layer
    |
    +---- Gmail tasks
    +---- AI tasks
    +---- Attachment tasks
    +---- Persistence tasks
```

Concurrency limits must be configurable or centrally controlled.

---

# 42. Event Bus

An internal event bus may be used for decoupling components.

Examples:

```text
EmailReceived
EventProcessed
AIAnalysisCompleted
NotificationRequested
NotificationDisplayed
ProcessingFailed
TopicChanged
```

The event bus must not become an uncontrolled global dependency.

Its use should be limited to genuinely asynchronous/domain events.

---

# 43. Internal Events vs External Events

The architecture must distinguish:

### External Events

```text
Gmail Pub/Sub notification
YouTube webhook
RSS update
```

### Internal Events

```text
IntelligenceEventCreated
AIAnalysisCompleted
NotificationRequested
ContentGenerationRequested
```

External events must be validated before entering the internal event model.

---

# 44. Configuration Architecture

Configuration should be centralized.

Conceptually:

```text
Application Settings
       |
       +--> Gmail
       +--> AI
       +--> Notifications
       +--> Topics
       +--> Attachments
       +--> Database
       +--> Logging
       +--> Content
```

Configuration should be strongly typed and validated at startup.

---

# 45. Security Architecture

Security-sensitive information must be isolated.

```text
Application
     |
     v
Secret Provider
     |
     +--> Windows Credential Store
     +--> Secure Token Storage
```

Secrets should never be ordinary application configuration.

---

# 46. Observability Architecture

The application should provide:

```text
Structured Logging
Metrics
Processing IDs
Health Status
Error Tracking
```

Example processing trace:

```text
EVENT-12345

Received
  14:01:03.120

Retrieved
  14:01:03.620

AI Started
  14:01:04.010

AI Completed
  14:01:06.430

Persisted
  14:01:06.510

Notification
  14:01:06.650
```

---

# 47. Health Monitoring

A health service may expose:

```text
Gmail Health
Pub/Sub Health
AI Health
Database Health
Notification Health
Storage Health
```

Health state should be available to the UI.

---

# 48. Error Architecture

Errors should be classified.

```text
Domain Error
Application Error
Infrastructure Error
External Provider Error
Configuration Error
Security Error
Validation Error
```

Infrastructure errors should be translated into application-level errors where appropriate.

---

# 49. Retry Architecture

Retry behavior should be centralized.

```text
Operation
   |
   v
Error Classifier
   |
   +--> Non-Retryable -> FAILED
   |
   +--> Retryable
          |
          v
     Retry Policy
          |
          v
     Retry Queue
```

Business logic should not contain scattered retry loops.

---

# 50. Circuit Breaker Direction

Future external integrations may use circuit breakers.

Example:

```text
AI Provider
   |
Repeated failures
   |
Circuit Open
   |
Temporary bypass
   |
Recovery test
   |
Circuit Closed
```

This is not required for MVP unless testing demonstrates the need.

---

# 51. Application Boundary

The desktop application is the initial deployment boundary.

```text
+-----------------------------------------------------+
|                  InsightFlow Desktop                |
|                                                     |
| UI                                                  |
| Application                                         |
| Domain                                              |
| Infrastructure                                     |
| Local Database                                     |
+-----------------------------------------------------+
       |          |             |
       v          v             v
    Gmail       Pub/Sub       Bedrock
```

---

# 52. Cloud Boundary

Google Cloud Pub/Sub is an external cloud dependency used for Gmail push events.

```text
Windows
   |
   | HTTPS / secure connection
   v
Google Cloud Pub/Sub
   |
   v
Gmail event notification
```

The application must authenticate securely with the cloud service.

---

# 53. Real-Time Architecture

The desired real-time path is:

```text
                  Gmail
                    |
                    v
              Gmail Watch
                    |
                    v
           Google Cloud Pub/Sub
                    |
                    v
          Push / Event Receiver
                    |
                    v
            Event Processing
                    |
                    v
             AI Processing
                    |
                    v
            Priority Engine
                    |
                    v
          Notification Queue
                    |
                    v
           Windows Popup
```

The architecture must not insert an artificial polling delay.

---

# 54. Story Intelligence Architecture

Future story grouping:

```text
Incoming Event
      |
      v
Event Similarity
      |
      +---- Existing Story ---> Update Story
      |
      +---- New Story --------> Create Story
```

Story updates may trigger:

```text
AI Story Summary
Timeline Update
Notification
Content Generation
```

---

# 55. Search Architecture

Initial:

```text
SQLite
   |
   v
Full Text Search
   |
   v
Search Service
   |
   v
UI
```

Future:

```text
Natural Language Query
       |
       v
AI Query Understanding
       |
       v
Search Engine
       |
       v
Relevant Events/Stories
```

---

# 56. Future AI Chat Architecture

```text
User Question
      |
      v
Chat Service
      |
      v
Query Understanding
      |
      v
Search / Retrieval
      |
      v
Relevant Intelligence
      |
      v
AI Provider
      |
      v
Answer
```

The chat system must use stored intelligence rather than blindly sending the entire database to an AI model.

---

# 57. Future YouTube Content Architecture

```text
Important Story
      |
      v
Content Workflow
      |
      +--> Research Context
      |
      +--> Script
      |
      +--> Voice
      |
      +--> Visuals
      |
      +--> Video
      |
      +--> Thumbnail
      |
      +--> Metadata
      |
      v
Approval
      |
      v
YouTube
```

This subsystem must remain optional and must not affect normal email intelligence processing.

---

# 58. Plugin Architecture

The system should support plugin-style providers.

Conceptually:

```text
Plugin Registry
      |
      +--> Source Plugins
      +--> AI Plugins
      +--> Notification Plugins
      +--> Attachment Plugins
      +--> Content Plugins
      +--> Publishing Plugins
```

Plugins must expose defined contracts.

---

# 59. Plugin Isolation

A failing plugin should not crash the entire application.

Example:

```text
RSS Plugin Failed
      |
      v
Gmail Monitoring Continues
```

---

# 60. Domain Independence

The domain layer must not know:

```text
PySide6
boto3
google-api-python-client
google-cloud-pubsub
SQLite
SQLAlchemy
Windows APIs
```

This is a hard architectural boundary.

---

# 61. Infrastructure Independence

Infrastructure adapters may know external technologies.

For example:

```text
GmailAdapter
    -> Gmail API SDK

BedrockProvider
    -> boto3

SQLiteRepository
    -> SQLAlchemy/SQLite

WindowsNotificationProvider
    -> Windows/PySide6 APIs
```

These dependencies must remain outside the domain.

---

# 62. Presentation Independence

The application layer must not know individual UI widgets.

For example, this is prohibited:

```text
Application Service
    -> QMessageBox
    -> QLabel
    -> QWidget
```

Instead:

```text
Application Service
    -> Result / Event
        |
        v
Presentation
    -> Widget
```

---

# 63. Testing Architecture

Testing should occur at multiple levels:

```text
Unit Tests
    |
    v
Application Tests
    |
    v
Integration Tests
    |
    v
End-to-End Tests
```

Unit tests should dominate the test suite.

---

# 64. Test Doubles

External providers must have test doubles.

Examples:

```text
FakeGmailProvider
FakeAIProvider
FakeNotificationProvider
FakeRepository
FakeAttachmentStorage
```

This allows deterministic testing.

---

# 65. Deployment Architecture

Development:

```text
Python
Virtual Environment
SQLite
Local configuration
```

Production:

```text
Windows Installer
Packaged Application
Secure credentials
SQLite database
User configuration
```

---

# 66. Update Architecture

Future application updates should preserve:

```text
Database
Topics
AI Profiles
Rules
Settings
```

unless a migration explicitly requires otherwise.

Database migrations must be versioned.

---

# 67. Recommended Project Boundary

The architecture should eventually resemble:

```text
src/
    domain/
    application/
    infrastructure/
    presentation/
    shared/
```

Detailed folder structure will be defined in:

```text
05_System_Design.md
```

This document intentionally defines architectural responsibilities without locking every directory name yet.

---

# 68. Architecture Decision: Desktop-First

The initial product is desktop-first because:

- The primary user is on Windows.
- Desktop notifications are central.
- Gmail monitoring should continue in the background.
- Local history/database is useful.
- System tray operation is required.

A future cloud service can be introduced without redesigning the domain.

---

# 69. Architecture Decision: Modular Monolith

The initial system should be a **modular monolith**, not microservices.

Reason:

```text
One user
+
Desktop application
+
Early product stage
=
Microservices would add unnecessary complexity
```

Modules must have clean boundaries so that individual components can later be extracted if required.

---

# 70. Why Not Microservices Initially?

Microservices would introduce:

- More deployments.
- More networking.
- More authentication.
- More operational complexity.
- More failure modes.
- More infrastructure.
- More development overhead.

The product does not initially require that complexity.

---

# 71. Future Evolution

If the platform grows substantially:

```text
Desktop Client
       |
       v
API Gateway
       |
       +--> Source Service
       +--> Intelligence Service
       +--> AI Service
       +--> Workflow Service
       +--> Content Service
       +--> Publishing Service
       |
       v
Database / Event Infrastructure
```

The modular-monolith architecture should make this evolution possible.

---

# 72. Architecture Risks

Important risks include:

### Gmail Push Complexity

Gmail push/watch requires correct Google Cloud configuration and renewal/maintenance of the watch subscription.

### AI Latency

AI processing may dominate end-to-end notification latency.

### AI Cost

Large numbers of alerts may produce unnecessary AI costs.

### Duplicate Alerts

Google Alerts may send repetitive content.

### Notification Overload

High-frequency topics may overwhelm the user.

### Attachment Security

Attachments are untrusted content.

### AI Hallucination

Generated interpretations must be clearly separated from source facts.

### Overengineering

The platform must not build future infrastructure before it is needed.

---

# 73. Architecture Principles for AI Coding Agents

Every AI coding agent working on the project must follow these rules:

1. Do not bypass architectural layers.
2. Do not call external APIs from UI code.
3. Do not access the database directly from UI code.
4. Do not put Gmail-specific logic into the domain.
5. Do not put Bedrock-specific logic into the domain.
6. Do not hardcode topic-specific behavior.
7. Do not hardcode AI prompts in application services.
8. Do not create global singleton state without architectural justification.
9. Do not introduce microservices for convenience.
10. Do not duplicate existing provider abstractions.
11. Do not weaken tests to make implementation pass.
12. Do not silently change requirements.
13. Create an ADR for significant architectural changes.

---

# 74. Architecture Quality Attributes

The architecture is explicitly optimized for:

```text
Modularity       ██████████
Testability      ██████████
Extensibility    ██████████
Reliability      █████████
Security         █████████
Maintainability  ██████████
Performance      ████████
Simplicity       ████████
```

The goal is balanced engineering rather than maximizing one attribute at the expense of all others.

---

# 75. End-to-End Architecture Summary

The complete initial architecture is:

```text
                    +----------------+
                    |     Gmail      |
                    +-------+--------+
                            |
                     Gmail Watch
                            |
                            v
                    +---------------+
                    | Google Cloud  |
                    |   Pub/Sub     |
                    +-------+-------+
                            |
                            v
+----------------------------------------------------------+
|                 InsightFlow Desktop                      |
|                                                          |
|  +---------------- Presentation ----------------------+  |
|  | PySide6 | Dashboard | Settings | Tray | Popups    |  |
|  +------------------------+----------------------------+  |
|                           |                             |
|  +------------------------v----------------------------+  |
|  |                Application Layer                    |  |
|  | Use Cases | Processing | Workflows | Queries       |  |
|  +------------------------+----------------------------+  |
|                           |                             |
|  +------------------------v----------------------------+  |
|  |                  Domain Layer                       |  |
|  | Topics | Events | AI Analysis | Stories | Rules    |  |
|  +------------------------+----------------------------+  |
|                           ^                             |
|  +------------------------+----------------------------+  |
|  |               Infrastructure Layer                 |  |
|  | Gmail | Pub/Sub | Bedrock | SQLite | Windows       |  |
|  | Attachments | Storage | Future Providers          |  |
|  +-----------------------------------------------------+  |
|                                                          |
+----------------------------------------------------------+
              |              |               |
              v              v               v
           Gmail         Bedrock          SQLite
```

---

# 76. Final Architectural Principle

The central architectural principle is:

> **External systems provide information and capabilities; the InsightFlow domain and application layers decide how that information is transformed into intelligence and actions.**

Therefore:

```text
Gmail is a source, not the application.

Claude is an AI provider, not the intelligence model.

PySide6 is a presentation technology, not the business logic.

SQLite is a persistence mechanism, not the domain.

YouTube is a publishing destination, not the content model.
```

This separation is what allows InsightFlow AI to evolve from:

```text
Gmail Monitor
```

into:

```text
AI Intelligence Platform
```

and eventually:

```text
AI Intelligence + Content Automation + Publishing Platform
```

without requiring a fundamental rewrite of the core.
