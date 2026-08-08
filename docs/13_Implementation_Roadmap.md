# InsightFlow AI — Implementation Roadmap

**Document:** `13_Implementation_Roadmap.md`  
**Status:** Implementation Baseline  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `00` through `12`

---

# 1. Purpose

This document converts the InsightFlow AI architecture and design documentation into an executable development roadmap.

It is specifically intended for:

- Cursor
- Codex
- Claude Code
- Other AI coding agents
- Human developers

The roadmap defines:

```text
What to build
In what order
Why the order matters
What must be tested
When a phase is complete
What an AI agent must not do
```

The objective is to reach a working Windows application incrementally rather than asking an AI coding agent to build the entire system in one operation.

---

# 2. Implementation Philosophy

The project will be built:

```text
Small
Incremental
Testable
Executable
Verifiable
```

The rule is:

> **Never move to the next major phase while the current phase has unresolved architectural or functional failures.**

---

# 3. Overall Roadmap

```text
Phase 0   Development Environment
Phase 1   Project Skeleton
Phase 2   Configuration and Logging
Phase 3   Domain Model
Phase 4   Database and Repositories
Phase 5   Application Use Cases
Phase 6   Basic Windows UI
Phase 7   Gmail OAuth
Phase 8   Gmail Label Discovery
Phase 9   Gmail Watch + Pub/Sub
Phase 10  Real-Time Event Pipeline
Phase 11  AI Provider
Phase 12  AI Analysis and Summary
Phase 13  Notification System
Phase 14  Dashboard and Intelligence UI
Phase 15  Attachment Handling
Phase 16  Reliability and Recovery
Phase 17  Testing and Quality Hardening
Phase 18  Windows Packaging
Phase 19  Production Readiness
Phase 20  Future Story/YouTube Pipeline
```

---

# 4. Golden Rule for AI Coding Agents

An AI coding agent must NOT be given:

```text
"Build the entire application."
```

Instead, give it:

```text
One phase
+
One milestone
+
One clearly defined task
+
Acceptance criteria
```

---

# 5. Agent Working Procedure

For every task, the agent must:

```text
1. Read relevant documentation.
2. Inspect existing code.
3. Identify affected layers.
4. State the implementation plan.
5. Implement the smallest appropriate change.
6. Add/update tests.
7. Run validation.
8. Review the diff.
9. Report results.
```

---

# 6. Documentation Reading Order

Before implementation begins, the agent should understand:

```text
00 Project Vision
01 Product Requirements
02 Functional Requirements
03 Non-Functional Requirements
04 System Architecture
05 System Design
06 Database Design
07 UI/UX Design
08 SOLID & Design Patterns
09 Project Structure & Coding Standards
10 Interface & API Contracts
11 Gmail Real-Time Monitoring Design
12 AI Analysis & Summary Design
13 Implementation Roadmap
```

For an isolated task, the agent may focus on the relevant documents, but must consult the architecture and contract documents whenever boundaries are affected.

---

# 7. Phase 0 — Development Environment

## Objective

Create a reproducible development environment.

## Tasks

```text
Install/verify Python
Create virtual environment
Initialize Git
Configure editor
Configure formatter
Configure linter
Configure type checker
Configure pytest
Create .env.example
Create .gitignore
```

Recommended tools:

```text
Python 3.13+
pytest
Ruff
mypy or pyright
```

## Acceptance Criteria

```text
[ ] Python version is documented.
[ ] Virtual environment works.
[ ] Tests can execute.
[ ] Formatter works.
[ ] Linter works.
[ ] Type checker works.
[ ] Git repository is clean.
[ ] No secrets are committed.
```

---

# 8. Phase 1 — Project Skeleton

## Objective

Create the architecture-defined directory structure.

Expected:

```text
src/insightflow/
├── domain/
├── application/
├── infrastructure/
├── presentation/
├── configuration/
├── shared/
└── bootstrap/
```

Tests:

```text
tests/
├── unit/
├── integration/
├── architecture/
└── e2e/
```

## Acceptance Criteria

```text
[ ] Project imports successfully.
[ ] Package structure matches document 09.
[ ] Basic application entry point exists.
[ ] pytest discovers tests.
[ ] Architecture import rules can be tested.
```

---

# 9. Phase 2 — Configuration and Logging

## Objective

Build configuration and observability foundations before external integrations.

## Tasks

```text
Typed configuration
Environment handling
Application directories
Secure secret-store abstraction
Structured logging
Correlation ID
Runtime diagnostics
```

## Acceptance Criteria

```text
[ ] Application starts with default configuration.
[ ] Invalid configuration produces clear errors.
[ ] Logs are structured.
[ ] Secrets are not logged.
[ ] Runtime directories are created safely.
[ ] Correlation IDs are supported.
```

---

# 10. Phase 3 — Domain Model

## Objective

Implement the core business model independently of Gmail, AI and UI.

## Core Models

```text
Topic
IntelligenceEvent
AIProfile
AIAnalysis
Attachment
Notification
Story
ContentJob
```

Implement:

```text
Value objects
Enums
Domain exceptions
Domain events
Policies where required
```

## Acceptance Criteria

```text
[ ] Domain imports no infrastructure modules.
[ ] Domain imports no PySide6.
[ ] Entities have meaningful invariants.
[ ] Important states use enums/value objects.
[ ] Domain tests pass.
```

---

# 11. Phase 4 — Database and Repositories

## Objective

Persist the application state locally.

Initial database:

```text
SQLite
```

## Tasks

```text
Database connection
Schema migrations
Tables
Repositories
Mappers
Unit of Work
Transactions
Indexes
Constraints
```

## Important Tables

At minimum, design/implement the documented equivalents of:

```text
topics
intelligence_events
ai_profiles
ai_analyses
attachments
notifications
monitoring_state
processing_jobs
audit_records
```

Exact schema must follow `06_Database_Design.md`.

## Acceptance Criteria

```text
[ ] Database initializes through migrations.
[ ] Repositories work.
[ ] Transactions work.
[ ] Duplicate event protection exists.
[ ] Repository tests pass.
[ ] No raw SQL exists outside infrastructure.
```

---

# 12. Phase 5 — Application Use Cases

## Objective

Implement the application layer independently of external providers.

Core use cases:

```text
CreateTopic
UpdateTopic
EnableTopic
DisableTopic
GetTopics
GetDashboard
GetEventDetails
SearchEvents
ProcessIntelligenceEvent
AnalyzeEvent
RequestNotification
DownloadAttachment
ReprocessAI
```

## Acceptance Criteria

```text
[ ] Use cases depend on contracts.
[ ] No Gmail SDK in application.
[ ] No AI provider SDK in application.
[ ] No PySide6 in application.
[ ] Unit tests cover core workflows.
```

---

# 13. Phase 6 — Basic Windows UI

## Objective

Create a functioning PySide6 shell before connecting Gmail.

Initial UI:

```text
Main Window
 ├── Dashboard
 ├── Intelligence
 ├── Topics
 ├── Notifications
 ├── Settings
 └── Diagnostics
```

## Tasks

```text
Application startup
Navigation
ViewModels
DTO binding
Basic styling
Tray support
```

## Acceptance Criteria

```text
[ ] GUI starts.
[ ] GUI remains responsive.
[ ] Navigation works.
[ ] No database/network calls block UI thread.
[ ] ViewModels communicate with application layer.
```

---

# 14. Phase 7 — Gmail OAuth

## Objective

Connect the application securely to Gmail.

## Tasks

```text
Google Cloud project configuration
Gmail API enablement
OAuth configuration
Secure credential storage
Token refresh
Connect/disconnect
Account identity
```

## Acceptance Criteria

```text
[ ] User can authorize Gmail.
[ ] Credentials are securely stored.
[ ] Token refresh works.
[ ] Disconnect works.
[ ] Authentication failures are handled.
[ ] No credentials appear in logs.
```

---

# 15. Phase 8 — Gmail Label Discovery

## Objective

Allow the user to select which Gmail labels should be monitored.

## Flow

```text
Connect Gmail
    ↓
Load labels
    ↓
Display labels
    ↓
User selects label
    ↓
Create Topic
```

## Acceptance Criteria

```text
[ ] Gmail labels can be retrieved.
[ ] Label IDs are stored.
[ ] Label names are displayed.
[ ] Topic can reference a label.
[ ] Missing labels are detected.
[ ] No topic is hardcoded.
```

---

# 16. Phase 9 — Gmail Watch + Pub/Sub

## Objective

Implement the event-driven Gmail monitoring mechanism.

## Tasks

```text
Google Cloud Pub/Sub topic
Pub/Sub subscription
Gmail watch
Watch renewal
Pub/Sub subscriber
Message parsing
Acknowledgement
Reconnect
Monitoring state
```

## Acceptance Criteria

```text
[ ] Gmail watch can be established.
[ ] Pub/Sub receives Gmail notifications.
[ ] Application receives notifications.
[ ] Watch expiration is tracked.
[ ] Watch renewal works.
[ ] Subscriber reconnects after temporary failure.
[ ] Duplicate Pub/Sub messages are safe.
```

---

# 17. Phase 10 — Real-Time Event Pipeline

## Objective

Convert Gmail changes into durable intelligence events.

## Flow

```text
Pub/Sub
   ↓
History ID
   ↓
Gmail History
   ↓
Message IDs
   ↓
Message Retrieval
   ↓
Label Filtering
   ↓
Deduplication
   ↓
NormalizedSourceEvent
   ↓
IntelligenceEvent
   ↓
Database
```

## Acceptance Criteria

```text
[ ] New labeled email creates event.
[ ] Duplicate delivery does not duplicate event.
[ ] Message IDs are persisted.
[ ] History progress is safe.
[ ] Application restart is recoverable.
[ ] Unmonitored labels are ignored.
[ ] Disabled topics are handled correctly.
```

---

# 18. Phase 11 — AI Provider

## Objective

Introduce the provider-independent AI boundary.

Initial provider:

```text
AWS Bedrock
```

## Tasks

```text
AIProvider interface
AI request model
AI response model
Bedrock adapter
Provider error translation
Timeout
Retry classification
FakeAIProvider
```

## Acceptance Criteria

```text
[ ] Application sees only AIProvider.
[ ] Bedrock SDK stays in infrastructure.
[ ] Fake provider works.
[ ] Provider failures are translated.
[ ] Timeout works.
[ ] No real AI dependency exists in unit tests.
```

---

# 19. Phase 12 — AI Analysis and Summary

## Objective

Convert every eligible intelligence event into validated AI intelligence.

## Tasks

```text
AI profiles
Prompt builder
Source preprocessing
Prompt injection protection
Structured output
Schema validation
AIAnalysis persistence
AI job queue
Retry
Profile versioning
```

## Initial output

```text
Summary
Why it matters
Key facts
What to watch
Market impact where configured
Confidence
```

## Acceptance Criteria

```text
[ ] Any topic can use an AI profile.
[ ] No topic-specific AI code exists.
[ ] Structured output is validated.
[ ] Invalid output is handled.
[ ] AI failures do not lose events.
[ ] Re-analysis is supported.
[ ] Model/profile versions are retained.
```

---

# 20. Phase 13 — Windows Notification System

## Objective

Implement the user's requested bottom-right desktop notification experience.

## Flow

```text
AI Analysis
   ↓
Priority Engine
   ↓
Notification Policy
   ↓
Notification Queue
   ↓
Windows Popup
```

## Popup Requirements

```text
Bottom-right
Fade in
Display
Fade out
Non-blocking
Clickable
Priority-aware
```

## Acceptance Criteria

```text
[ ] Popup appears at bottom-right.
[ ] Fade-in/out works.
[ ] Popup does not block application.
[ ] Multiple notifications are queued/coalesced.
[ ] High-priority events are visible quickly.
[ ] User can open event/source.
```

---

# 21. Phase 14 — Dashboard and Intelligence UI

## Objective

Connect the UI to real application data.

## Dashboard

Display:

```text
Monitoring status
Recent intelligence
Important events
AI summaries
Topic activity
Processing status
Unread count
```

## Intelligence Screen

Display:

```text
Topic
Headline
Priority
Summary
Time
Source
```

## Event Details

Display:

```text
Full summary
Why it matters
Facts
What to watch
Market impact
AI metadata
Attachments
Source
```

## Acceptance Criteria

```text
[ ] Real events appear without manual refresh.
[ ] UI updates from internal events.
[ ] No Gmail polling by UI.
[ ] Search/filter works.
[ ] Event details work.
```

---

# 22. Phase 15 — Attachment Handling

## Objective

Implement optional attachment downloading and processing.

Supported architecture:

```text
PDF
Excel
CSV
ZIP
Text
Image
Future types
```

## Modes

```text
DISABLED
MANUAL
AUTO
AUTO_SELECTED_TYPES
```

## Acceptance Criteria

```text
[ ] Attachment download can be disabled.
[ ] Manual download works.
[ ] Filename is sanitized.
[ ] Size limits work.
[ ] ZIP traversal is prevented.
[ ] Attachments never execute automatically.
[ ] Processing failures do not lose the email event.
```

---

# 23. Phase 16 — Reliability and Recovery

## Objective

Make the application resilient enough for continuous use.

Test and implement:

```text
Application restart
Internet outage
Gmail authentication expiration
Gmail watch expiration
Pub/Sub disconnect
History gap
AI provider outage
Database failure
Windows sleep/resume
Network change
Duplicate messages
```

## Acceptance Criteria

```text
[ ] Temporary failures recover automatically where possible.
[ ] Permanent failures request user action.
[ ] No silent data loss.
[ ] Duplicate processing is safe.
[ ] Monitoring status accurately reflects reality.
```

---

# 24. Phase 17 — Testing and Quality Hardening

## Objective

Establish confidence before packaging.

## Unit Tests

```text
Domain
Policies
Use cases
Prompt builder
Validators
Repositories
```

## Integration Tests

```text
SQLite
Gmail
Pub/Sub
AI provider
Notification provider
```

## Architecture Tests

Verify:

```text
Domain -> no infrastructure
Application -> no provider SDK
Application -> no GUI
Presentation -> no SQL
```

## E2E Tests

At minimum:

```text
Synthetic Gmail event
    ↓
Event processing
    ↓
AI
    ↓
Notification
    ↓
UI
```

---

# 25. Phase 18 — Windows Packaging

## Objective

Create a usable Windows application package.

Possible packaging technology:

```text
PyInstaller
```

or another appropriate Windows packaging solution.

## Tasks

```text
Executable build
Application icon
Version information
Configuration handling
Runtime directories
Logging
Installer/package
```

## Acceptance Criteria

```text
[ ] Application runs on clean Windows environment.
[ ] Python does not need to be installed separately.
[ ] Configuration works.
[ ] Database works.
[ ] Notifications work.
[ ] Logs work.
[ ] Upgrade path is documented.
```

---

# 26. Phase 19 — Production Readiness

## Objective

Prepare the application for continuous personal use.

## Tasks

```text
Security review
Credential review
Logging review
Performance testing
AI cost review
Gmail quota review
Database backup
Recovery procedure
Configuration backup
Error diagnostics
Release versioning
```

## Acceptance Criteria

```text
[ ] No secrets in repository.
[ ] Secure credential storage verified.
[ ] Monitoring recovery tested.
[ ] Database backup/restore tested.
[ ] AI costs understood.
[ ] Real-time behavior verified.
[ ] Failure notifications verified.
```

---

# 27. Phase 20 — Future Story and YouTube Pipeline

This phase is intentionally after the monitoring product is stable.

## Flow

```text
Intelligence Events
      ↓
Story Grouping
      ↓
Deep AI Analysis
      ↓
Fact Consolidation
      ↓
3-Minute Script
      ↓
Human Review
      ↓
Video Generation
      ↓
YouTube Upload
```

## Do Not Implement Early

The YouTube pipeline must NOT delay:

```text
Gmail monitoring
AI summaries
Desktop notifications
Dashboard
```

---

# 28. MVP Definition

The first usable MVP should contain:

```text
Gmail connection
+
Label selection
+
Real-time Gmail monitoring
+
Topic management
+
AI summary
+
Priority
+
Windows popup
+
Event history
+
Dashboard
```

Optional attachment handling can be included but must not block the core MVP.

---

# 29. MVP Explicitly Excludes

The first MVP does not need:

```text
Automatic YouTube publishing
Advanced video generation
Multiple AI providers
Multiple Gmail accounts
Complex story intelligence
Automatic trading
Cloud backend
Mobile application
Microservices
Kubernetes
```

These remain future extensions.

---

# 30. First Vertical Slice

Before building every feature, create one complete working path:

```text
One Gmail label
      ↓
One configured topic
      ↓
One Gmail event
      ↓
One AI profile
      ↓
One AI summary
      ↓
One Windows popup
      ↓
One stored event
```

This is the most important early milestone.

---

# 31. Vertical Slice Acceptance Test

The developer should be able to:

```text
1. Configure Gmail.
2. Select a test label.
3. Send/create an email matching that label.
4. Receive the event through Gmail Watch/Pub/Sub.
5. Store the event.
6. Analyze it using AI.
7. Display the summary.
8. Show a bottom-right popup.
9. Open the source.
10. Restart the application.
11. Confirm the event remains available.
```

---

# 32. Second Vertical Slice

After the first slice:

```text
Multiple Labels
      ↓
Multiple Topics
      ↓
Different AI Profiles
      ↓
Different Notification Policies
```

Acceptance:

```text
Trump
Iran-US
Celebrity X
```

can coexist without source-code changes.

---

# 33. Third Vertical Slice

Add:

```text
Attachments
Search
Filters
Diagnostics
Retry
Recovery
```

---

# 34. Fourth Vertical Slice

Production hardening:

```text
Packaging
Startup
Shutdown
Sleep/resume
Network recovery
Database recovery
Quota handling
```

---

# 35. Recommended Implementation Order Within Each Phase

Use:

```text
1. Data model
2. Contract
3. Implementation
4. Unit tests
5. Integration test
6. UI integration
7. End-to-end test
```

Do not start with UI if the underlying contract is undefined.

---

# 36. Definition of Done

A task is DONE only when:

```text
[ ] Code implemented.
[ ] Relevant tests implemented.
[ ] Tests pass.
[ ] Formatter passes.
[ ] Linter passes.
[ ] Type checker passes where applicable.
[ ] Architecture boundaries preserved.
[ ] Documentation updated if behavior/architecture changed.
[ ] No secrets added.
[ ] No unrelated refactoring introduced.
```

---

# 37. AI Agent Task Template

Every Cursor/Codex task should follow this format:

```text
TASK

Implement:
<one specific capability>

READ FIRST

<relevant documents>

SCOPE

<files/modules that may be changed>

DO NOT CHANGE

<unrelated areas>

REQUIREMENTS

<precise requirements>

ACCEPTANCE CRITERIA

<testable conditions>

TESTS

<tests that must be added/run>

REPORT

Explain:
- files changed
- implementation
- tests
- limitations
- architecture impact
```

---

# 38. Example Agent Task — Gmail Label Discovery

```text
TASK

Implement Gmail label discovery.

READ FIRST

09_Project_Structure_and_Coding_Standards.md
10_Interface_and_API_Contracts.md
11_Gmail_RealTime_Monitoring_Design.md

SCOPE

infrastructure/gmail
application/services
relevant tests

DO NOT CHANGE

AI implementation
Windows notification implementation
YouTube functionality

REQUIREMENTS

Retrieve Gmail labels through the Gmail adapter.
Return normalized label objects.
Do not expose Google SDK models.
Handle authentication and API errors.

ACCEPTANCE CRITERIA

A fake Gmail provider can return labels.
Application receives normalized labels.
Google SDK types do not cross the infrastructure boundary.
Tests pass.
```

---

# 39. Example Agent Task — AI Summary

```text
TASK

Implement structured AI summary processing for one IntelligenceEvent.

READ FIRST

10_Interface_and_API_Contracts.md
12_AI_Analysis_and_Summary_Design.md

REQUIREMENTS

Use AIProvider.
Use configured AIProfile.
Validate structured output.
Persist AIAnalysis.
Handle invalid responses.
Do not block Gmail monitoring.

ACCEPTANCE CRITERIA

Fake AI provider test passes.
Invalid response test passes.
Successful analysis is persisted.
```

---

# 40. Agent Rules During Implementation

Agents must:

```text
Prefer existing abstractions.
Search before creating.
Implement smallest change.
Add regression tests.
Respect contracts.
Keep provider SDKs behind adapters.
Keep UI responsive.
Avoid magic values.
Avoid unrelated refactoring.
```

---

# 41. Agent Forbidden Actions

Agents must not:

```text
Rewrite entire architecture.
Replace SQLite without approval.
Replace PySide6 without approval.
Introduce microservices.
Introduce Docker/Kubernetes unnecessarily.
Add REST API without requirement.
Hardcode news topics.
Hardcode Gmail labels.
Hardcode AI provider behavior.
Add credentials to code.
Disable TLS verification.
Use polling instead of push architecture.
Block GUI thread.
Skip tests.
Silently change database schema.
```

---

# 42. Dependency Addition Rule

Before adding a dependency, the agent must explain:

```text
Why it is needed.
Why standard library is insufficient.
Why existing dependencies cannot provide it.
Maintenance/security implications.
```

---

# 43. Database Change Rule

Any schema change requires:

```text
Migration
Model/repository update
Tests
Documentation review
```

Never modify the development database manually and call that the implementation.

---

# 44. Contract Change Rule

Any interface change requires:

```text
Search consumers
Search implementations
Update interface
Update implementations
Update tests
Review architecture
```

---

# 45. UI Change Rule

UI changes must not introduce:

```text
SQL
Gmail SDK
AI SDK
business rules
```

inside widgets/views.

---

# 46. Real-Time Rule

No implementation may introduce:

```text
30-second polling
60-second polling
```

as the primary Gmail monitoring mechanism.

The primary mechanism remains:

```text
Gmail Watch
+
Pub/Sub
+
History API
```

---

# 47. AI Rule

No implementation may hardcode:

```text
Trump
Iran
Modi
Celebrity X
Company X
```

into business logic.

Topics are data.

---

# 48. AI Output Rule

No code should directly trust:

```text
raw model text
```

for important business decisions.

Use:

```text
Structured response
+
Validation
```

---

# 49. Notification Rule

Notifications must be driven by:

```text
NotificationPolicy
```

not directly by:

```text
AI provider
```

---

# 50. Reliability Rule

For external operations:

```text
Assume duplicate delivery.
Assume timeout.
Assume temporary failure.
Assume application restart.
```

Design accordingly.

---

# 51. Observability Rule

Every important asynchronous workflow should be traceable using:

```text
correlation_id
event_id
job_id
timestamps
```

---

# 52. Security Rule

Never commit:

```text
OAuth client secret
Refresh token
API key
AWS secret
Private credential
```

---

# 53. Development/Test Environment

Development should support:

```text
Fake Gmail
Fake Pub/Sub
Fake AI
Fake Notification
SQLite test database
```

so most development does not require external services.

---

# 54. Real External Integration Tests

External integration tests should be:

```text
Explicit
Optional
Clearly marked
Isolated
```

They must not run automatically in every unit-test execution unless intentionally configured.

---

# 55. CI Pipeline

Future CI should run:

```text
Install
↓
Format check
↓
Lint
↓
Type check
↓
Unit tests
↓
Architecture tests
↓
Integration tests where configured
↓
Build
```

---

# 56. Development Milestones

## Milestone 1 — Skeleton

```text
Project starts
Tests run
Architecture exists
```

## Milestone 2 — Persistence

```text
Topics/events stored
```

## Milestone 3 — Gmail

```text
Gmail connected
Labels discovered
```

## Milestone 4 — Real-Time

```text
Gmail → Pub/Sub → Event
```

## Milestone 5 — Intelligence

```text
Event → AI → Summary
```

## Milestone 6 — Alerting

```text
Summary → Windows Popup
```

## Milestone 7 — Usable Product

```text
Dashboard
Search
History
Diagnostics
```

## Milestone 8 — Reliable Product

```text
Recovery
Packaging
Security
Testing
```

---

# 57. Suggested Development Sequence

The practical sequence should be:

```text
Week/Iteration 1
    Project + tooling
        ↓
    Domain + database

Week/Iteration 2
    Application layer
        ↓
    Basic UI

Week/Iteration 3
    Gmail OAuth
        ↓
    Label management

Week/Iteration 4
    Gmail Watch
        ↓
    Pub/Sub
        ↓
    Real-time events

Week/Iteration 5
    AI provider
        ↓
    AI summary

Week/Iteration 6
    Windows notifications
        ↓
    Dashboard

Week/Iteration 7
    Attachments
        ↓
    Recovery
        ↓
    Testing

Week/Iteration 8
    Packaging
        ↓
    Production hardening
```

These are planning iterations, not mandatory calendar commitments.

---

# 58. First Development Session

The first actual coding session should NOT begin with Gmail.

Start with:

```text
Phase 0
+
Phase 1
+
basic Phase 2
```

Then verify the project foundation.

---

# 59. First Coding Prompt to AI Agent

Recommended first prompt:

```text
Read the following documents before making changes:

00_Project_Vision.md
04_System_Architecture.md
08_SOLID_and_Design_Patterns.md
09_Project_Structure_and_Coding_Standards.md
10_Interface_and_API_Contracts.md
13_Implementation_Roadmap.md

Task:

Create the initial Python project skeleton for InsightFlow AI.

Requirements:

- Python 3.13+
- src/insightflow package
- Domain/application/infrastructure/presentation/configuration/shared/bootstrap structure
- tests/unit, tests/integration, tests/architecture, tests/e2e
- pyproject.toml
- pytest configuration
- Ruff configuration
- type checker configuration
- .env.example
- .gitignore
- minimal application entry point
- no Gmail implementation
- no AI implementation
- no UI implementation beyond a minimal startup placeholder

Do not introduce unnecessary dependencies.

Add tests proving the package imports correctly.

Run formatting, linting, type checking and tests.

Report all files created and validation results.
```

---

# 60. Second Coding Prompt

After Phase 1 is verified:

```text
Implement Phase 2: configuration and logging foundations.

Read:
09_Project_Structure_and_Coding_Standards.md
10_Interface_and_API_Contracts.md
13_Implementation_Roadmap.md

Implement only:
- typed configuration
- application directories
- structured logging
- correlation ID
- secure secret-store interface
- development configuration

Do not implement Gmail, AI, UI workflows or database functionality.

Add unit tests.

Run all available validation.
```

---

# 61. Vertical Slice Strategy

After foundational phases, stop thinking in terms of:

```text
"Build module A completely."
```

Prefer:

```text
Build one end-to-end capability.
```

Example:

```text
Gmail
 ↓
Event
 ↓
AI
 ↓
Popup
```

This exposes architectural problems early.

---

# 62. Why This Strategy Matters

AI coding agents can generate large amounts of code very quickly.

The biggest risk is not:

```text
Not enough code
```

It is:

```text
Too much code built on an incorrect assumption.
```

Small vertical slices reduce that risk.

---

# 63. Checkpoint Rule

At the end of each major phase:

```text
STOP
```

Then verify:

```text
Tests
Architecture
Behavior
Performance
Security
Documentation
```

Only then continue.

---

# 64. Architecture Freeze Point

After:

```text
Phase 5
```

the core architecture should become relatively stable.

Changes after that should be driven by real implementation evidence rather than speculation.

---

# 65. Gmail Freeze Point

After:

```text
Phase 10
```

the real-time event contract should be treated as stable.

Later features should consume events rather than modifying Gmail monitoring unnecessarily.

---

# 66. AI Freeze Point

After:

```text
Phase 12
```

the AI analysis contract should be stable enough that:

```text
Notifications
Dashboard
Future Story system
```

can consume it independently.

---

# 67. Notification Freeze Point

After:

```text
Phase 13
```

the application should be capable of providing the primary user experience:

```text
New information
→
AI summary
→
Desktop notification
```

---

# 68. MVP Freeze Point

After:

```text
Phase 14
```

we should have a usable personal version.

At this point:

```text
STOP adding major features.
```

Use the application with real alerts.

Collect real-world observations.

---

# 69. Real-World Validation Period

Use actual user-configured topics such as:

```text
Trump
Iran-US
US Market
Modi
Celebrity
Other personal topics
```

Measure:

```text
Delivery latency
Summary usefulness
False alerts
Duplicate alerts
AI quality
Notification frequency
Gmail reliability
```

---

# 70. Do Not Optimize Prematurely

Initially avoid:

```text
Complex caching
Distributed queues
Microservices
Vector databases
Kubernetes
Large event infrastructure
```

Use the simplest architecture that satisfies real requirements.

---

# 71. Future Scaling

If the application later requires:

```text
Multiple users
Cloud deployment
Large-scale event volume
Multiple workers
Centralized monitoring
```

then components can be extracted because the contracts already exist.

---

# 72. Future Multi-User Architecture

Potential future:

```text
Desktop Client
       |
       v
Cloud API
       |
       +--> Gmail Service
       +--> AI Service
       +--> Event Store
       +--> Notification Service
       +--> Content Service
```

This is not part of the MVP.

---

# 73. Future YouTube Phase

Only after the intelligence system proves useful:

```text
Collect related events
        ↓
Build story
        ↓
Generate script
        ↓
Review
        ↓
Generate video
        ↓
Publish
```

The existing AIAnalysis contract becomes an input to the story pipeline.

---

# 74. Final Roadmap Summary

```text
                    FOUNDATION
                       |
                       v
             Project + Configuration
                       |
                       v
                 Domain + DB
                       |
                       v
                 Application
                       |
                       v
                  Basic UI
                       |
                       v
                Gmail OAuth
                       |
                       v
               Gmail Labels
                       |
                       v
            Gmail Watch + Pub/Sub
                       |
                       v
              Real-Time Events
                       |
                       v
                   AI Layer
                       |
                       v
              AI Summaries
                       |
                       v
            Windows Notifications
                       |
                       v
                 Dashboard
                       |
                       v
             Attachments/Recovery
                       |
                       v
               Testing/Hardening
                       |
                       v
               Windows Packaging
                       |
                       v
              Production MVP
                       |
                       v
             Future Story Engine
                       |
                       v
               YouTube Pipeline
```

---

# 75. Final Implementation Principle

The project should evolve in this order:

```text
Correctness
    ↓
Reliability
    ↓
Usability
    ↓
Performance
    ↓
Optimization
    ↓
Automation
```

Do not reverse this order.

---

# 76. Final Acceptance Criteria for the Entire Project

The initial production-ready application is complete when:

```text
[ ] User can connect Gmail.
[ ] User can select any Gmail label.
[ ] User can create any topic.
[ ] No news subject is hardcoded.
[ ] Gmail changes arrive through event-driven monitoring.
[ ] No 30/60-second polling is required for normal operation.
[ ] Duplicate delivery is safe.
[ ] Events are stored locally.
[ ] AI generates validated summaries.
[ ] AI profile is configurable.
[ ] AI provider is abstracted.
[ ] AI failure does not lose events.
[ ] Priority/impact is calculated.
[ ] Windows popup appears bottom-right.
[ ] Popup fades in/out.
[ ] Notifications are priority-aware.
[ ] User can open original source.
[ ] Attachments are optional.
[ ] Attachment security is enforced.
[ ] Dashboard shows live intelligence.
[ ] Search/history works.
[ ] Monitoring status is accurate.
[ ] Reconnection works.
[ ] Watch renewal works.
[ ] History recovery works.
[ ] Application restart is safe.
[ ] Windows packaging works.
[ ] Security review passes.
[ ] Tests pass.
```

---

# 77. Final Development Philosophy

> **Build the smallest working version of the real system, prove it works, and then expand it.**

The most important early outcome is not a large codebase.

It is this:

```text
A real Gmail alert
      ↓
arrives in real time
      ↓
is understood by AI
      ↓
is summarized correctly
      ↓
appears as a useful Windows notification
      ↓
is stored for later investigation
```

Once that loop is reliable, everything else becomes an incremental extension.

---

# 78. Final Project Vision

The long-term system is:

```text
                     USER
                      |
                      v
              +---------------+
              | InsightFlow AI|
              +-------+-------+
                      |
       +--------------+--------------+
       |              |              |
       v              v              v
    Monitor         Analyze       Notify
       |              |              |
       v              v              v
     Gmail            AI          Windows
       |              |          Desktop
       +--------------+--------------+
                      |
                      v
                 Intelligence
                      |
                      v
                   Stories
                      |
                      v
                Future Content
                      |
                      v
                 YouTube
```

The implementation roadmap ensures that this long-term vision is built without compromising the simplicity, reliability, and maintainability of the initial personal-use application.
