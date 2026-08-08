# InsightFlow AI — Non-Functional Requirements

**Document:** `03_Non_Functional_Requirements.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `00_Project_Vision.md`, `01_Product_Requirements.md`, `02_Functional_Requirements.md`

---

# 1. Purpose

This document defines the non-functional requirements (NFRs) for InsightFlow AI.

Functional requirements define **what the application does**.

Non-functional requirements define **how well, how safely, how reliably, and under what operational constraints the application must perform those functions**.

These requirements are especially important because InsightFlow AI is intended to process information in near real time and may eventually become an always-running desktop intelligence and content automation platform.

---

# 2. NFR Categories

The requirements are organized into:

```text
Performance
Real-Time Responsiveness
Reliability
Availability
Resilience
Scalability
Security
Privacy
Data Integrity
Observability
Maintainability
Testability
Extensibility
Usability
Accessibility
UI Responsiveness
Resource Usage
Configuration
Deployment
Recovery
Compatibility
AI Reliability
Cost Control
Content Safety
```

---

# 3. Requirement Identification

Requirements use these identifiers:

```text
NFR-PERF-xxx     Performance
NFR-RT-xxx       Real-time behavior
NFR-REL-xxx      Reliability
NFR-AVL-xxx      Availability
NFR-RES-xxx      Resilience
NFR-SCALE-xxx    Scalability
NFR-SEC-xxx      Security
NFR-PRIV-xxx     Privacy
NFR-DATA-xxx     Data integrity
NFR-OBS-xxx      Observability
NFR-MAINT-xxx    Maintainability
NFR-TEST-xxx     Testability
NFR-EXT-xxx      Extensibility
NFR-UX-xxx       Usability
NFR-A11Y-xxx     Accessibility
NFR-UI-xxx       UI responsiveness
NFR-RESOURCE-xxx Resource usage
NFR-CONFIG-xxx   Configuration
NFR-DEPLOY-xxx   Deployment
NFR-REC-xxx      Recovery
NFR-COMP-xxx     Compatibility
NFR-AI-xxx       AI reliability
NFR-COST-xxx     Cost control
NFR-CONTENT-xxx  Content safety
```

---

# 4. Performance Requirements

## NFR-PERF-001 — UI Responsiveness

The application UI shall remain responsive while:

- Gmail APIs are called.
- Pub/Sub events are processed.
- AI requests are running.
- Attachments are downloaded.
- Attachments are processed.
- Database operations occur.
- Search is performed.

Long-running operations must never execute directly on the GUI thread.

### Target

For normal user interaction, the UI should respond to input within approximately:

```text
< 100 ms preferred
< 250 ms acceptable for ordinary operations
```

Longer operations shall display progress/status rather than freezing the application.

---

## NFR-PERF-002 — Application Startup

The application should become interactive quickly after startup.

Target for a normal local installation:

```text
Application window/tray available: <= 5 seconds
```

External provider initialization may continue asynchronously.

The UI should not wait for all external systems before becoming interactive.

---

## NFR-PERF-003 — Database Search

Common local searches should complete quickly.

Target:

```text
Typical search: < 500 ms
```

Large searches may take longer, but the UI must remain responsive.

---

## NFR-PERF-004 — Notification Display

Once a processed event has been approved for notification, the notification service should display it promptly.

Target:

```text
Notification creation -> desktop display: < 1 second
```

under normal local conditions.

---

# 5. Real-Time Requirements

## NFR-RT-001 — Event Detection

The application shall prioritize event-driven source integrations.

For Gmail, Gmail push/watch with Google Cloud Pub/Sub is preferred over fixed-interval polling.

---

## NFR-RT-002 — End-to-End Latency

For normal Gmail operation, the target is:

```text
Email available in Gmail
        |
        v
Push event
        |
        v
Message retrieval
        |
        v
AI processing
        |
        v
Desktop notification
```

Target:

```text
P50: <= 10 seconds
P95: <= 30 seconds
```

These are engineering targets rather than guaranteed Gmail service-level guarantees.

External provider latency must be measured separately.

---

## NFR-RT-003 — No Artificial Polling Delay

The application must not intentionally wait 30/60 seconds before processing a Gmail event when a push event is available.

---

## NFR-RT-004 — Real-Time Status

The UI shall show monitoring state such as:

```text
Connected
Waiting for events
Processing
Paused
Connection Error
Reconnecting
```

---

# 6. Reliability Requirements

## NFR-REL-001 — No Silent Data Loss

An event that has been received but not successfully processed shall not simply disappear.

It must have a persistent or recoverable state such as:

```text
PENDING
PROCESSING
RETRY_PENDING
FAILED
COMPLETED
IGNORED
DUPLICATE
```

---

## NFR-REL-002 — Idempotency

Repeated delivery of the same external event must not create unintended duplicate processing.

The system should use stable identifiers such as:

```text
Gmail Message ID
External Event ID
Source + External ID
```

where appropriate.

---

## NFR-REL-003 — Retry

Temporary failures shall support controlled retries.

Examples:

- Network timeout.
- Gmail API temporary failure.
- Pub/Sub temporary failure.
- AI provider timeout.
- Temporary database lock.

Retries should use exponential backoff where appropriate.

---

## NFR-REL-004 — Maximum Retry

Retries must have a bounded limit.

An operation that repeatedly fails shall eventually enter a persistent failure state rather than retrying indefinitely.

---

## NFR-REL-005 — Recovery Queue

Failed operations should remain available for:

- Automatic retry.
- Manual retry.
- Inspection.
- Error diagnosis.

---

# 7. Availability

## NFR-AVL-001 — Desktop Availability

The application should be capable of running continuously for long periods without requiring frequent restarts.

Target for normal operation:

```text
24 hours continuous operation
```

without memory/resource degradation caused by known application defects.

---

## NFR-AVL-002 — Graceful Degradation

If one external service fails, unrelated local functionality should continue when possible.

Example:

```text
Gmail: Connected
Database: Connected
AI: Unavailable
UI: Operational
History: Available
```

The application should not terminate merely because the AI provider is temporarily unavailable.

---

## NFR-AVL-003 — Reconnection

External connections should support automatic reconnection where safe.

---

# 8. Resilience

## NFR-RES-001 — Network Failure

Temporary loss of internet connectivity must not crash the application.

---

## NFR-RES-002 — Provider Failure

External provider failures must be isolated.

Examples:

```text
Gmail failure
AWS Bedrock failure
Pub/Sub failure
YouTube failure
```

One provider must not unnecessarily destabilize unrelated components.

---

## NFR-RES-003 — Application Restart

After an unexpected application restart, the system should identify incomplete work and recover it safely.

---

## NFR-RES-004 — Crash Safety

The application should avoid partially committed database state.

Transactions must be used where multiple related records must be updated atomically.

---

# 9. Scalability

## NFR-SCALE-001 — Topic Scalability

The application should support multiple simultaneously monitored topics.

Initial target:

```text
10–50 active topics
```

without architectural changes.

---

## NFR-SCALE-002 — Event Scalability

Initial target:

```text
Up to 1,000 processed events/day
```

without significant degradation on a normal modern desktop.

The architecture should not prevent future scaling beyond this.

---

## NFR-SCALE-003 — AI Concurrency

AI requests should be controlled through a bounded worker/concurrency mechanism.

The application must not launch unlimited AI requests if many events arrive simultaneously.

---

## NFR-SCALE-004 — Notification Burst

If many events arrive together:

- Processing must remain controlled.
- Notifications must be queued/stacked.
- The UI must remain usable.
- The application must avoid notification storms.

---

# 10. Security Requirements

## NFR-SEC-001 — No Password Storage

The application must never store Gmail passwords.

---

## NFR-SEC-002 — Secret Management

The following must never be committed to source control:

```text
OAuth client secrets
OAuth tokens
AWS access keys
API keys
YouTube credentials
Encryption keys
Passwords
```

---

## NFR-SEC-003 — Credential Protection

Credentials/tokens must be stored using an appropriate secure mechanism for Windows.

The implementation should prefer the Windows credential/security facilities or an equivalent secure secret store rather than plaintext configuration files.

---

## NFR-SEC-004 — Least Privilege

External APIs should request only the permissions required for the application's functionality.

---

## NFR-SEC-005 — Sensitive Logs

Logs must not expose:

- Access tokens.
- Refresh tokens.
- API keys.
- Passwords.
- Authorization headers.
- Full sensitive email bodies unless explicitly enabled for diagnostics.

---

## NFR-SEC-006 — Input Validation

External content must be treated as untrusted input.

This includes:

- Email content.
- HTML.
- Attachments.
- AI responses.
- Web content.
- Metadata.

---

## NFR-SEC-007 — Attachment Security

Attachments must be treated as untrusted files.

The application must:

- Validate file type.
- Validate size.
- Avoid unsafe automatic execution.
- Prevent unsafe archive extraction.
- Avoid path traversal.
- Sanitize filenames.

---

# 11. Privacy Requirements

## NFR-PRIV-001 — Data Minimization

Only information required for processing should be transmitted to external services.

---

## NFR-PRIV-002 — AI Provider Transparency

The user must be able to identify which AI provider/model is processing their information.

---

## NFR-PRIV-003 — Local Data

The application should clearly identify what information is stored locally.

Examples:

```text
Email metadata
Email content
AI summaries
Attachments
Processing logs
```

---

## NFR-PRIV-004 — Retention

The application should support configurable retention policies.

Possible settings:

```text
7 days
30 days
90 days
1 year
Forever
```

Exact defaults will be decided during system design.

---

## NFR-PRIV-005 — Delete Data

The user should eventually be able to delete:

- Individual processed items.
- Topic history.
- Attachments.
- AI results.
- Entire local history.

Deletion behavior must be clearly communicated.

---

# 12. Data Integrity

## NFR-DATA-001 — Transactional Updates

Related database updates must be atomic where required.

---

## NFR-DATA-002 — Unique External IDs

External identifiers should be protected against unintended duplication.

---

## NFR-DATA-003 — Referential Integrity

Relationships between:

```text
Topic
Source
Event
AI Result
Notification
Attachment
Story
Content
```

must remain consistent.

---

## NFR-DATA-004 — Database Backup

The application should provide a mechanism for backing up the local database.

---

## NFR-DATA-005 — Database Recovery

A valid backup should be restorable without manually editing database files.

---

# 13. Observability

## NFR-OBS-001 — Structured Logging

Logs should use structured fields where practical.

Example:

```text
timestamp
level
component
operation
event_id
topic_id
source_id
duration
status
error
```

---

## NFR-OBS-002 — Correlation ID

A processing operation should have a correlation identifier where practical.

Example:

```text
EVENT-20260808-000123
```

This allows the complete lifecycle to be traced.

---

## NFR-OBS-003 — Processing Metrics

The application should collect local metrics such as:

```text
Events received
Events processed
AI successes
AI failures
Average AI latency
Notifications shown
Duplicates detected
Attachments processed
Errors
```

---

## NFR-OBS-004 — Health Status

The dashboard should provide a basic health view:

```text
Gmail       Healthy
Pub/Sub     Healthy
AI          Healthy
Database    Healthy
Notifier    Healthy
```

---

# 14. Maintainability

## NFR-MAINT-001 — Separation of Concerns

The application must maintain clear boundaries between:

```text
Domain
Application
Infrastructure
Presentation
```

---

## NFR-MAINT-002 — SOLID

Code should follow SOLID principles.

Particular emphasis:

- Single Responsibility.
- Dependency Inversion.
- Open/Closed.

---

## NFR-MAINT-003 — Type Safety

Python code should use type hints consistently.

Static type checking should be introduced.

---

## NFR-MAINT-004 — Code Quality

The project should use automated tooling for:

```text
Formatting
Linting
Type Checking
Testing
```

Exact tools will be finalized in the engineering standards document.

---

## NFR-MAINT-005 — Documentation

Public interfaces and non-obvious design decisions should be documented.

Architecture decisions shall be recorded through ADRs where appropriate.

---

# 15. Testability

## NFR-TEST-001 — Unit Testability

Domain logic must be testable without:

- Gmail.
- Internet.
- AWS.
- Google Cloud.
- Windows UI.

---

## NFR-TEST-002 — Integration Testing

External integrations should have integration tests that can run against test/sandbox resources where practical.

---

## NFR-TEST-003 — Mockable Providers

External providers must be replaceable with mocks/fakes in tests.

---

## NFR-TEST-004 — Deterministic Core Logic

Core rules such as:

```text
Priority
Deduplication
Topic resolution
Notification policy
State transitions
```

should be deterministic and highly testable.

---

## NFR-TEST-005 — AI Testing

AI behavior is probabilistic.

Testing should therefore include:

- Schema validation.
- Contract tests.
- Representative fixtures.
- Prompt regression tests.
- Safety tests.
- Fallback behavior.

The system must not depend exclusively on exact text matching for AI tests.

---

# 16. Extensibility

## NFR-EXT-001 — New Source

Adding a new source should not require rewriting the domain layer.

---

## NFR-EXT-002 — New AI Provider

Adding a new AI provider should not require modifying topic logic.

---

## NFR-EXT-003 — New Notification Provider

Future notification mechanisms should be addable independently.

Examples:

```text
Desktop
Email
Telegram
WhatsApp
Slack
```

---

## NFR-EXT-004 — New Content Provider

Future publishing providers should be independently implementable.

---

# 17. Usability

## NFR-UX-001 — Configuration

A user should be able to configure a topic without editing source code.

---

## NFR-UX-002 — Status Visibility

The user should always be able to understand whether monitoring is:

```text
Active
Paused
Disconnected
Error
```

---

## NFR-UX-003 — Notification Clarity

A notification should be understandable without opening the full email.

---

## NFR-UX-004 — Minimal Cognitive Load

Notifications should show the most important information first:

```text
Priority
Headline
Summary
Impact
Action
```

---

## NFR-UX-005 — Advanced Controls

Advanced configuration should be available without making the default workflow complicated.

---

# 18. Accessibility

## NFR-A11Y-001

The application should support:

- Keyboard navigation.
- Readable font sizes.
- Appropriate contrast.
- Visible focus state.
- Tooltips for unfamiliar controls.
- Screen-reader-friendly labels where supported by the UI framework.

---

# 19. UI Responsiveness

## NFR-UI-001

No network operation may block the GUI thread.

---

## NFR-UI-002

No AI operation may block the GUI thread.

---

## NFR-UI-003

No large attachment operation may block the GUI thread.

---

## NFR-UI-004

Long-running operations should expose progress/status.

Example:

```text
Downloading attachment...
Processing PDF...
Waiting for AI...
Generating summary...
```

---

# 20. Resource Usage

## NFR-RESOURCE-001 — CPU

When idle, the application should use minimal CPU.

The application should not continuously consume significant CPU while waiting for Gmail push events.

---

## NFR-RESOURCE-002 — Memory

The application should avoid unbounded memory growth.

Large email bodies and attachments should not remain unnecessarily in memory.

---

## NFR-RESOURCE-003 — Disk

Logs, attachments, and database growth must be controlled.

Retention settings should prevent uncontrolled disk usage.

---

## NFR-RESOURCE-004 — Attachment Processing

Large files should be processed using streaming/chunking where appropriate rather than loading entire files into memory unnecessarily.

---

# 21. Configuration

## NFR-CONFIG-001 — Centralized Configuration

Configuration should be centralized and strongly typed.

---

## NFR-CONFIG-002 — Environment Separation

The application should support separate configurations for:

```text
Development
Testing
Production
```

---

## NFR-CONFIG-003 — Secrets Separation

Secrets must not be mixed with ordinary configuration.

---

## NFR-CONFIG-004 — Validation

Invalid configuration should be detected early and reported clearly.

---

# 22. Deployment

## NFR-DEPLOY-001 — Windows

Version 1 shall target modern supported Windows desktop environments.

---

## NFR-DEPLOY-002 — Installer

The production application should eventually be distributed using a Windows installer.

---

## NFR-DEPLOY-003 — Python Dependency

The end user should not need to install Python separately for the packaged production application.

---

## NFR-DEPLOY-004 — Upgrade

Future releases should support safe application upgrades without unnecessarily deleting user data.

---

# 23. Recovery

## NFR-REC-001 — Restart Recovery

The application must recover unfinished processing after restart where possible.

---

## NFR-REC-002 — Configuration Recovery

Application configuration should survive normal application updates.

---

## NFR-REC-003 — Database Recovery

The application should provide a documented backup/restore procedure.

---

## NFR-REC-004 — Provider Reconnection

The application should automatically attempt reconnection to temporary external failures.

---

# 24. Compatibility

## NFR-COMP-001 — Windows

The initial supported platform is Windows.

---

## NFR-COMP-002 — Python

Development should use a supported Python 3.x version defined by the project environment.

---

## NFR-COMP-003 — External API Versions

External APIs must be isolated so that provider API changes have limited impact on the application.

---

# 25. AI Reliability

## NFR-AI-001 — Structured Output

Where structured output is required, AI responses must be schema-validated.

---

## NFR-AI-002 — No Hallucinated Facts

The application should instruct AI systems to distinguish known source facts from interpretation.

The UI should avoid presenting generated assumptions as confirmed facts.

---

## NFR-AI-003 — Source Grounding

AI analysis should be grounded primarily in the source content supplied to it.

If external research is later introduced, external sources should be explicitly identified.

---

## NFR-AI-004 — Confidence

Where appropriate, AI output should include confidence.

Confidence must not be interpreted as statistical certainty unless the underlying methodology supports that interpretation.

---

## NFR-AI-005 — Provider Failure

If AI is unavailable, the original information must remain available.

The system must never fabricate a fallback summary.

---

## NFR-AI-006 — Prompt Versioning

The exact prompt/profile version used for an analysis must be traceable.

---

# 26. AI Cost Control

## NFR-COST-001

The application should avoid unnecessary AI calls.

Examples:

- Do not reprocess exact duplicates.
- Avoid unnecessary processing of ignored topics.
- Use cached results where safe.
- Avoid sending irrelevant metadata.
- Avoid repeatedly summarizing the same story unless a meaningful change occurred.

---

## NFR-COST-002

The user should eventually be able to configure:

```text
Maximum AI spend/day
Maximum AI requests/hour
Maximum input size
Preferred model
Fallback model
```

---

## NFR-COST-003

The application should expose basic AI usage information:

```text
Requests
Approximate tokens where available
Estimated cost where provider data permits
Failures
Average latency
```

---

# 27. Content Generation Safety

## NFR-CONTENT-001

Future content-generation workflows must preserve the distinction between:

```text
Source Facts
AI Interpretation
Generated Narrative
```

---

## NFR-CONTENT-002

Generated YouTube content must not automatically be published in the initial release.

Human approval is required.

---

## NFR-CONTENT-003

Generated content should retain references to the source information used to create it.

---

# 28. Future Multi-Source Requirements

The architecture should support a future where one topic receives information from multiple sources.

Example:

```text
TRUMP

Gmail
RSS
News API
YouTube
Web
```

The system should normalize these into a common intelligence model.

---

# 29. Future Multi-User Considerations

Version 1 is intended primarily for a single Windows user.

However, the design should avoid assumptions that make future multi-user support impossible.

User-specific data should be separable conceptually from global system metadata.

---

# 30. Operational Targets

Initial engineering targets:

| Area | Target |
|---|---:|
| UI ordinary response | < 250 ms |
| Preferred UI response | < 100 ms |
| Application interactive startup | <= 5 sec |
| Notification display after decision | < 1 sec |
| Gmail event-to-notification P50 | <= 10 sec |
| Gmail event-to-notification P95 | <= 30 sec |
| Continuous operation target | 24 hours |
| Initial active topics | 10–50 |
| Initial processed events | <= 1,000/day |
| Typical search | < 500 ms |

These are **engineering targets**, not external provider guarantees.

They should be measured during development and revised based on real-world evidence.

---

# 31. Quality Gates

A release should not be considered production-ready unless:

```text
[ ] Unit tests pass
[ ] Integration tests pass
[ ] Static analysis passes
[ ] Type checking passes
[ ] No known critical security issue
[ ] No known data-loss issue
[ ] Startup works
[ ] Shutdown works
[ ] Restart recovery works
[ ] Gmail reconnection works
[ ] AI failure is handled
[ ] Duplicate events are handled
[ ] UI remains responsive
[ ] Logging works
[ ] Configuration validation works
[ ] Backup/restore procedure is tested
```

---

# 32. Performance Measurement

Performance must eventually be measured rather than assumed.

The application should record timestamps for important stages:

```text
source_received_at
message_retrieved_at
normalized_at
ai_started_at
ai_completed_at
stored_at
notification_created_at
notification_displayed_at
```

This enables calculation of:

```text
Source -> Retrieval
Retrieval -> AI
AI -> Persistence
Persistence -> Notification
End-to-End Latency
```

---

# 33. Failure Budget Philosophy

The system should distinguish between:

### Expected External Failures

Examples:

- Gmail temporary outage.
- Network timeout.
- AI rate limit.

These should trigger retry/recovery.

### Application Failures

Examples:

- Database corruption.
- Unhandled exception.
- State inconsistency.

These require engineering attention.

The monitoring/logging system should make this distinction visible.

---

# 34. Long-Term Scalability Direction

The initial application may use:

```text
Windows Desktop
+
SQLite
+
Gmail
+
Google Cloud Pub/Sub
+
AWS Bedrock
```

The architecture should eventually permit:

```text
Desktop Client
        |
        v
Local/Cloud API
        |
        +--> Source Workers
        |
        +--> AI Workers
        |
        +--> Workflow Engine
        |
        +--> Database
        |
        +--> Content Pipeline
        |
        +--> Publishing
```

The first implementation should not prematurely introduce distributed infrastructure unless required.

---

# 35. Important Non-Functional Principle

The application must optimize for:

```text
Reliability
    >
Correctness
    >
Security
    >
Maintainability
    >
Performance
    >
Feature Count
```

A feature that is fast but unreliable is not acceptable for an intelligence platform.

A feature that looks impressive but silently loses events is not acceptable.

---

# 36. Definition of Done for NFRs

A non-functional requirement is considered implemented only when:

1. It has a measurable or observable criterion.
2. The implementation addresses it.
3. The requirement has an appropriate test or verification method.
4. Results are documented where useful.
5. The requirement does not depend on undocumented assumptions.

---

# 37. Final Non-Functional Principle

InsightFlow AI should behave like a reliable background intelligence service even though its initial implementation is a Windows desktop application.

The user should experience:

```text
Information arrives
       |
       v
InsightFlow notices
       |
       v
AI understands
       |
       v
Important information appears quickly
       |
       v
History is preserved
       |
       v
Failures recover safely
```

The complexity required to make this reliable should remain inside the architecture rather than becoming the user's responsibility.

---

# 38. Governance

Changes to important NFRs must be reviewed against:

```text
00_Project_Vision.md
01_Product_Requirements.md
02_Functional_Requirements.md
03_Non_Functional_Requirements.md
```

Any change that materially affects architecture, security, performance, reliability, or scalability should result in an Architecture Decision Record (ADR).

AI coding agents must not silently relax an NFR to make an implementation easier.

