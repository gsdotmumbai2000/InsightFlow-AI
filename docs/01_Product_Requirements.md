# InsightFlow AI — Product Requirements Document

**Document:** `01_Product_Requirements.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Related Document:** `00_Project_Vision.md`

---

# 1. Purpose

This document defines the product requirements for InsightFlow AI.

The purpose of InsightFlow AI is to continuously collect information from configurable sources, process it using AI, identify relevant developments, generate concise and useful intelligence, notify the user in near real time, preserve the information for later search and analysis, and provide a foundation for future automated content creation and publishing.

The first release will focus on **Gmail label monitoring**, because Gmail/Google Alerts is the user's initial information-ingestion workflow.

The application must be designed so that Gmail is an initial source, not a permanent architectural limitation.

---

# 2. Product Vision Summary

InsightFlow AI should answer five questions:

1. **What happened?**
2. **Why does it matter?**
3. **How important is it?**
4. **What should I know or watch next?**
5. **What can I do with this information?**

For a trading-related topic, this may include potential market impact.

For a celebrity topic, it may include career or public-impact information.

For a technology topic, it may include product, security, or business implications.

The same platform must support all of these without hardcoded topic-specific business logic.

---

# 3. Target User

The initial product is designed for a technically capable individual who:

- Receives large volumes of information.
- Uses Google Alerts and Gmail labels to organize information.
- Wants near-real-time awareness.
- Wants AI to filter and summarize information.
- Monitors multiple unrelated topics.
- May use the information for trading, research, personal interests, or content creation.
- Wants to retain control over what is monitored and how it is interpreted.
- Uses Windows as the primary desktop environment.

The architecture should eventually support multiple users, but multi-user SaaS functionality is outside the initial scope.

---

# 4. Primary Use Case

## 4.1 Google Alert → Gmail → InsightFlow

Example workflow:

```text
Google Alert
     |
     v
Gmail
     |
     v
Gmail Label: TRUMP
     |
     v
InsightFlow AI
     |
     +--> Detect new message
     |
     +--> Extract content
     |
     +--> Identify topic
     |
     +--> Detect duplicates / related events
     |
     +--> AI Summary
     |
     +--> Topic-specific AI Analysis
     |
     +--> Priority
     |
     +--> Desktop Notification
     |
     +--> Store in local database
     |
     +--> Optional attachment processing
     |
     +--> Optional content generation
```

---

# 5. Product Scope

## 5.1 Version 1 Scope

Version 1 must include:

- Windows desktop application.
- Gmail OAuth authentication.
- Gmail label configuration.
- Gmail near-real-time notification mechanism.
- Gmail message retrieval.
- Message normalization.
- HTML/text email extraction.
- AI summarization.
- Configurable AI instructions per topic/label.
- Topic configuration.
- Priority calculation.
- Desktop popup notifications.
- Notification history.
- Local persistence.
- Searchable processed-email history.
- Duplicate detection foundation.
- Optional attachment download.
- Optional attachment processing.
- Application logging.
- Settings management.
- System tray operation.
- Error/retry handling.
- Basic dashboard.

## 5.2 Version 1.1 / Near-Term

Potential additions:

- Story grouping.
- Event timeline.
- Improved deduplication.
- AI chat over stored intelligence.
- More advanced rules.
- Multiple AI providers.
- RSS source.
- Additional notification channels.

## 5.3 Future Scope

Future releases may include:

- YouTube script generation.
- 3-minute video generation.
- Text-to-speech.
- Image/video generation.
- Thumbnail generation.
- YouTube upload.
- Scheduled publishing.
- RSS/news APIs.
- YouTube monitoring.
- Social media monitoring.
- Outlook.
- Telegram.
- Multi-user support.
- Cloud deployment.

---

# 6. Functional Requirements

## FR-001 — Application Startup

The application shall:

- Start as a Windows desktop application.
- Support normal window mode.
- Support minimized/system-tray mode.
- Display connection status.
- Display monitoring status.
- Load persisted configuration at startup.
- Restore the last known application state where appropriate.

### Acceptance Criteria

- Application starts without requiring a command-line window for normal users.
- Invalid configuration does not crash the application.
- Errors are shown through the UI and recorded in logs.

---

# 7. Gmail Integration

## FR-010 — Gmail Authentication

The application shall support Gmail OAuth 2.0 authentication.

Requirements:

- No Gmail username/password shall be stored.
- OAuth credentials shall be securely handled.
- Tokens shall be persisted securely where required.
- The user shall be able to disconnect the Gmail account.
- The user shall be able to reconnect.

### Acceptance Criteria

- User can authenticate using a Google account.
- Application can retrieve authorized Gmail data.
- Application shows authenticated account information.
- Revoked/expired authorization is handled gracefully.

---

## FR-011 — Gmail Label Selection

The user shall be able to retrieve and select Gmail labels.

Example:

```text
TRUMP
IRAN
MODI
NIFTY
CELEBRITY
AWS
OPENAI
```

The user shall not need to modify source code to add a label.

### Acceptance Criteria

- Available Gmail labels can be displayed.
- User can enable/disable monitoring for each label.
- Label configuration persists between application restarts.

---

# 8. Real-Time Monitoring

## FR-020 — Near-Real-Time Gmail Monitoring

The application shall use Gmail push notifications through Google Cloud Pub/Sub as the preferred mechanism.

The application shall not depend on a fixed 30-second or 60-second polling cycle for normal operation.

Conceptual flow:

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
Notification Receiver
  |
  v
InsightFlow
```

The system shall fetch the changed Gmail data after receiving the push notification.

### Important Constraint

Gmail push notification is an event signal, not the email content itself.

The application must retrieve the actual message through the Gmail API.

### Acceptance Criteria

- New monitored Gmail activity triggers processing without waiting for the next fixed polling interval.
- Duplicate push events do not create duplicate processing.
- Temporary Pub/Sub/Gmail failures are retried.
- Application restarts do not cause uncontrolled duplicate notifications.

---

# 9. Message Processing

## FR-030 — Email Retrieval

For a detected message, the application shall retrieve:

- Message ID.
- Thread ID.
- Sender.
- Recipients where available.
- Subject.
- Timestamp.
- Gmail labels.
- Plain-text body where available.
- HTML body where available.
- Attachment metadata.
- Gmail web URL where available.

---

## FR-031 — Email Normalization

The system shall convert provider-specific email information into a common internal representation.

This is required so future sources such as RSS or Outlook can use the same processing pipeline.

Conceptually:

```text
Gmail Email
     |
     v
Gmail Adapter
     |
     v
Common Document/Event
```

---

# 10. Topic Management

## FR-040 — Topic Creation

The user shall be able to create a topic.

A topic shall support:

- Name.
- Description.
- Source.
- Source identifier.
- AI profile.
- AI prompt.
- Priority.
- Notification configuration.
- Attachment configuration.
- Content-generation configuration.

Example:

```text
Topic: TRUMP

Source: Gmail

Label: TRUMP

AI Profile: Geopolitical Trading

Priority: High

Notification: Enabled

AI Summary: Enabled

Trading Analysis: Enabled

YouTube Generation: Enabled
```

---

## FR-041 — Topic Independence

Topics must operate independently.

Changing the configuration of:

```text
TRUMP
```

must not affect:

```text
CELEBRITY_X
```

or:

```text
AWS
```

No topic-specific code should be required.

---

# 11. AI Processing

## FR-050 — AI Summary

AI summarization is mandatory for the primary processing pipeline.

Every successfully processed monitored item shall receive an AI-generated summary unless the user explicitly configures an exception.

The summary should answer where applicable:

- What happened?
- Who is involved?
- What changed?
- Why does it matter?
- What is confirmed?
- What remains uncertain?

---

## FR-051 — Topic-Specific AI Analysis

Each topic may define custom AI instructions.

Example:

### Trading

```text
Analyze:

- Market relevance
- Potential affected assets
- Potential direction
- Risk
- Key events to monitor
- Confidence
```

### Celebrity

```text
Analyze:

- What happened
- Career relevance
- Major announcement
- Public reaction
- Important follow-up
```

### Technology

```text
Analyze:

- Product changes
- Business impact
- Security implications
- Competitive significance
```

The application must not hardcode these prompts.

---

# 12. AI Output Structure

AI responses should be represented using structured data rather than only storing unstructured text.

Potential fields:

```text
summary
headline
importance
priority
entities
events
facts
uncertainties
sentiment
topic_analysis
market_impact
confidence
recommended_followups
youtube_script
```

Only fields applicable to the configured AI profile need to be populated.

---

# 13. AI Provider Abstraction

## FR-060

The application shall use an AI provider abstraction.

Initial provider:

```text
AWS Bedrock / Claude
```

Future providers may include:

```text
OpenAI
Gemini
Ollama
Other providers
```

Business/domain logic must not directly depend on a specific AI provider.

---

# 14. Duplicate and Related Content

## FR-070 — Duplicate Detection

The system should identify:

- Exact duplicate emails.
- Repeated articles.
- Highly similar headlines.
- Repeated Google Alert content.

Duplicate information should not generate unnecessary repeated high-priority notifications.

---

## FR-071 — Story Grouping Foundation

The architecture shall allow related events to be grouped into a single evolving story.

Example:

```text
Iran-US Story

09:00 — Trump statement
10:20 — Iran response
11:30 — Oil price reaction
13:00 — US government update
```

Full story grouping may be implemented after the initial MVP.

---

# 15. Priority

Each processed item shall receive a priority.

Recommended initial levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Priority may depend on:

- User configuration.
- Topic.
- AI analysis.
- Event type.
- Confidence.
- Whether the event represents a meaningful change.

---

# 16. Desktop Notifications

## FR-080

The application shall provide Windows desktop notifications.

The notification shall appear near the bottom-right corner of the desktop.

Required behavior:

- Slide/fade in.
- Configurable display duration.
- Fade out.
- Multiple notifications can stack.
- Priority-aware presentation.
- User can dismiss.
- User can open source.
- User can view full AI analysis.

Example:

```text
+---------------------------------------+
| 🚨 HIGH IMPACT                        |
|                                       |
| Trump announces new Iran policy       |
|                                       |
| AI Summary                            |
| Diplomatic tensions increased...      |
|                                       |
| Market Impact                         |
| Oil ↑   Gold ↑   Nifty: Volatile      |
|                                       |
| [Open] [Details] [Dismiss]             |
+---------------------------------------+
```

---

# 17. Notification Rules

The user shall be able to configure:

- Notifications enabled/disabled.
- Minimum priority.
- Display duration.
- Sound enabled/disabled.
- Quiet hours.
- Topic-specific notification behavior.

Example:

```text
TRUMP
    HIGH/CRITICAL -> Notify
    MEDIUM        -> Notify
    LOW           -> Store only

CELEBRITY
    HIGH          -> Notify
    MEDIUM        -> Store
    LOW           -> Store
```

---

# 18. Attachment Processing

## FR-090

Attachment processing shall be optional.

Supported formats should include where practical:

- PDF
- XLSX
- XLS
- CSV
- DOCX
- ZIP
- Images

The user shall be able to configure:

```text
Download attachments: ON/OFF
Process attachments: ON/OFF
```

Attachment processing must not be mandatory for normal email summarization.

---

# 19. Attachment Storage

The user shall be able to configure the download directory.

Example:

```text
D:\InsightFlow\Attachments
```

Recommended organization:

```text
Attachments/
    2026/
        08/
            TRUMP/
            IRAN/
            AWS/
```

The exact storage design will be finalized in the database and system design documents.

---

# 20. Search

## FR-100

The application shall support searching processed information.

Search fields may include:

- Subject.
- Sender.
- Topic.
- Label.
- Date.
- AI summary.
- Entities.
- Priority.
- Event.
- Keywords.

Future versions should support natural-language AI search.

---

# 21. History

The application shall retain processing history.

A history record should allow the user to determine:

- When the email was received.
- When it was processed.
- Which AI provider was used.
- Which AI model was used.
- Which prompt/profile was used.
- What summary was generated.
- What priority was assigned.
- Whether a notification was displayed.
- Whether an attachment was processed.
- Whether content was generated.

---

# 22. Dashboard

The initial dashboard shall show:

```text
Connection Status
Monitoring Status
Active Topics
New Items
High Priority Items
AI Summaries Generated
Notifications
Attachment Processing
Processing Errors
```

The dashboard should not become the primary processing mechanism; it is a monitoring/control interface.

---

# 23. System Tray

The application shall support system-tray operation.

Tray menu should provide:

```text
Open
Pause Monitoring
Resume Monitoring
Topics
Settings
View Notifications
View Logs
About
Exit
```

---

# 24. Settings

Settings shall be categorized.

Suggested categories:

```text
General
Gmail
AI
Topics
Notifications
Attachments
Database
Security
Logging
Content Generation
YouTube
Advanced
```

---

# 25. Error Handling

The application shall gracefully handle:

- Network failures.
- Gmail API failures.
- OAuth failures.
- Pub/Sub failures.
- AI provider failures.
- AI timeouts.
- Invalid AI responses.
- Attachment errors.
- Database errors.
- Configuration errors.

Failures shall not silently disappear.

---

# 26. Retry Requirements

Retryable operations should support controlled retries.

Requirements:

- Exponential backoff where appropriate.
- Maximum retry count.
- Error classification.
- Dead-letter/error state.
- Logging.
- User visibility for persistent failures.

---

# 27. Idempotency

The system must be idempotent.

Processing the same Gmail notification more than once must not:

- Create duplicate documents.
- Generate duplicate notifications unnecessarily.
- Generate duplicate videos.
- Corrupt state.

A stable external identifier such as Gmail message ID must be used where appropriate.

---

# 28. Logging

The application shall use structured logging.

Logs should include:

- Timestamp.
- Component.
- Severity.
- Correlation ID where applicable.
- Operation.
- Error details.

Sensitive information must not be written to logs unnecessarily.

---

# 29. Security Requirements

The application shall:

- Never hardcode secrets.
- Never commit OAuth secrets or API keys.
- Protect tokens.
- Avoid storing passwords.
- Minimize sensitive data in logs.
- Clearly identify external AI processing.
- Provide secure configuration handling.
- Support data deletion/retention policies.

---

# 30. Performance Requirements

Initial targets:

- Application startup: reasonable desktop-app startup time.
- Event processing should begin promptly after Gmail notification.
- AI processing should not block the UI thread.
- Desktop UI must remain responsive during network/AI operations.
- Database operations must not block the UI.
- Multiple notifications must be handled without freezing the application.

Exact performance benchmarks will be established after the architecture prototype.

---

# 31. UI Requirements

The UI shall be Windows desktop-first.

Primary screens:

```text
Dashboard
Topics
Live Feed
Notifications
History
AI Analysis
Settings
Logs
About
```

The UI must separate presentation from business logic.

---

# 32. AI Chat — Future Requirement

The system should eventually allow natural-language questions over stored intelligence.

Examples:

```text
What changed about Trump today?

What Iran-related developments occurred today?

Show high-impact news from this morning.

What events could affect Nifty tomorrow?

Summarize this week's major developments.
```

This is not required for the first MVP but must be considered in the data model.

---

# 33. Content Generation

## FR-130 — Future YouTube Workflow

The system shall eventually support:

```text
Processed Story
      |
      v
AI Script
      |
      v
Narration
      |
      v
Visual Assets
      |
      v
Video
      |
      v
Thumbnail
      |
      v
Metadata
      |
      v
User Approval
      |
      v
YouTube
```

The initial version shall store enough structured intelligence to support this future workflow.

---

# 34. Three-Minute Video Requirement

The future content pipeline should support approximately three-minute videos.

The generated script should therefore consider:

- Target duration.
- Narration speed.
- Number of scenes.
- Visual transitions.
- Intro.
- Main story.
- Context.
- Conclusion.
- Call to action where appropriate.

Exact script length and narration settings will be defined in the content-generation specification.

---

# 35. Human Approval for Publishing

Initial YouTube workflow must require explicit user approval before publishing.

The application shall show:

```text
Generated Script
Generated Title
Description
Tags
Thumbnail Concept
Video Preview
```

The user can:

```text
Approve
Edit
Regenerate
Reject
```

Automatic publishing is a future opt-in capability.

---

# 36. Non-Functional Requirements

## NFR-001 — Maintainability

The application must use modular architecture and clear separation of responsibilities.

## NFR-002 — Extensibility

New sources, AI providers, notification mechanisms, and processing modules should be addable through interfaces/adapters.

## NFR-003 — Testability

Core business logic must be testable without Gmail, AWS, or the UI.

## NFR-004 — Reliability

The system must tolerate temporary failures without losing events.

## NFR-005 — Observability

The application must provide useful logs and status information.

## NFR-006 — Security

Credentials and sensitive data must be protected.

## NFR-007 — UI Responsiveness

Long-running work must never block the GUI thread.

## NFR-008 — Portability

The domain/application layers should not be tightly coupled to Windows, even though Windows is the initial target.

---

# 37. Architecture Constraints

The following constraints are mandatory:

1. UI must not contain business logic.
2. Domain must not depend on infrastructure.
3. Gmail-specific code must be isolated.
4. AI-provider-specific code must be isolated.
5. Prompts must not be hardcoded into business logic.
6. Database access must be isolated behind persistence abstractions.
7. External services must be accessed through adapters.
8. Long-running tasks must not execute on the UI thread.
9. Configuration must not be scattered throughout the codebase.
10. New topics must not require source-code changes.

---

# 38. MVP Definition

The MVP is complete when the following end-to-end flow works:

```text
Google Alert
     |
     v
Gmail Label
     |
     v
Gmail Push Notification
     |
     v
InsightFlow
     |
     v
Retrieve Email
     |
     v
Extract Content
     |
     v
AI Summary
     |
     v
Store Result
     |
     v
Windows Popup
```

A user must be able to:

1. Authenticate Gmail.
2. Select a Gmail label.
3. Configure an AI prompt/profile.
4. Receive a new Google Alert.
5. Have it processed automatically.
6. See an AI-generated summary.
7. Receive a desktop notification.
8. Open the original email.
9. Find the processed item later in history.
10. Restart the application without losing configuration.

---

# 39. MVP Exclusions

The first MVP will not require:

- Automatic YouTube upload.
- Automatic video generation.
- Social media publishing.
- Full AI chat.
- Multi-user cloud architecture.
- All possible source integrations.
- Fully autonomous trading decisions.
- Automated financial transactions.

These may be implemented later.

---

# 40. User Stories

## US-001 — Configure a Topic

As a user, I want to configure a Gmail label as a topic so that I can monitor a specific subject.

## US-002 — Real-Time Notification

As a user, I want to know about new information shortly after it arrives so that I do not have to repeatedly check Gmail.

## US-003 — AI Summary

As a user, I want an AI-generated summary so that I can understand the important information quickly.

## US-004 — Topic-Specific Analysis

As a user, I want different topics to have different AI instructions so that the analysis is relevant to each subject.

## US-005 — Trading Analysis

As a user, I want trading-related topics to include potential market implications so that I can prepare for possible market behavior.

## US-006 — Celebrity Monitoring

As a user, I want to monitor a specific celebrity without changing the application code.

## US-007 — Attachment Control

As a user, I want attachment processing to be optional so that I control storage and processing.

## US-008 — History

As a user, I want to search previous processed information so that I can review past developments.

## US-009 — Duplicate Filtering

As a user, I want repeated information to be recognized so that I do not receive unnecessary duplicate alerts.

## US-010 — Content Generation

As a future user, I want an important story converted into a YouTube script and video so that I can create content efficiently.

---

# 41. Acceptance Test — Example Trading Topic

Given:

```text
Gmail Label = TRUMP
AI Profile = Trading / Geopolitics
Notification = Enabled
```

When a new Google Alert arrives:

Then:

1. Gmail generates a push event.
2. InsightFlow receives the event.
3. The Gmail message is retrieved.
4. The email is normalized.
5. Duplicate status is checked.
6. AI processes the content.
7. A summary is generated.
8. Trading-related analysis is generated.
9. Priority is assigned.
10. The result is persisted.
11. A desktop notification is displayed.
12. The user can open the original email.
13. The processing operation is recorded in logs.

---

# 42. Acceptance Test — Celebrity Topic

Given:

```text
Gmail Label = CELEBRITY_X
AI Profile = Entertainment
Trading Analysis = Disabled
Notification = Enabled
```

When a new alert arrives:

Then:

- The same processing pipeline is used.
- The entertainment AI instructions are applied.
- Trading analysis is not generated.
- A relevant entertainment summary is displayed.
- The application does not require any source-code modification.

---

# 43. Acceptance Test — Attachment Disabled

Given:

```text
Download Attachments = OFF
```

When an email with a PDF arrives:

Then:

- Email processing continues.
- AI summary is generated.
- Attachment metadata may be recorded.
- PDF is not saved to disk.
- Application does not fail because the attachment was ignored.

---

# 44. Acceptance Test — Duplicate Alert

Given the same Gmail message/event is delivered more than once:

Then:

- The message is processed idempotently.
- Duplicate database records are not created.
- Duplicate high-priority notifications are not generated unnecessarily.

---

# 45. Product Principles

The following principles are mandatory:

### Principle 1 — Generic by Design

Do not hardcode topics.

### Principle 2 — AI Is Configurable

Do not hardcode analysis logic into topic handlers.

### Principle 3 — Real-Time First

Use event-driven mechanisms where possible.

### Principle 4 — Human in Control

AI recommends; the user decides.

### Principle 5 — Preserve Information

Important information should be searchable and auditable.

### Principle 6 — Build for Extension

Future sources and providers must fit through clear interfaces.

### Principle 7 — Fail Safely

External failures must not cause silent data loss.

### Principle 8 — UI Must Remain Responsive

Network, AI, database, and attachment processing must not freeze the GUI.

---

# 46. Definition of Done — Feature Level

A feature is not considered complete until:

- Requirements are understood.
- Design is documented where necessary.
- Code follows project architecture.
- Unit tests exist for business logic.
- Integration tests exist where appropriate.
- Error handling exists.
- Logging exists.
- Configuration is externalized.
- No secrets are hardcoded.
- Documentation is updated.
- AI-agent-generated code has been reviewed.
- Existing tests still pass.

---

# 47. Requirements Traceability

Each future implementation task should reference one or more requirements.

Example:

```text
TASK-001
Implement Gmail OAuth

Requirements:
FR-010
NFR-006
```

This allows the project to track whether every requirement is actually implemented and tested.

---

# 48. Requirement Change Policy

Requirements will evolve.

When a requirement changes:

1. Update this document.
2. Identify affected architecture/design documents.
3. Update ADRs if a technical decision changes.
4. Update tests.
5. Update implementation.
6. Record the change in project history.

AI coding agents must not silently change requirements.

---

# 49. Final Product Requirement

The most important product requirement is:

> **InsightFlow AI must allow the user to define what information matters to them and then continuously transform that information into understandable, timely, and reusable intelligence without requiring the user to manually inspect every incoming item.**

The first implementation uses Gmail labels and Google Alerts.

The architecture must be capable of growing far beyond Gmail into a general-purpose AI intelligence and content automation platform.
