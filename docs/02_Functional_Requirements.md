# InsightFlow AI — Functional Requirements

**Document:** `02_Functional_Requirements.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Document:** `01_Product_Requirements.md`

---

# 1. Purpose

This document defines the detailed functional behavior of InsightFlow AI.

`01_Product_Requirements.md` defines what the product must provide at a product level.

This document defines more precisely **how each functional capability is expected to behave** so that:

- developers can implement features consistently,
- Cursor and other AI coding agents can understand expected behavior,
- testers can create test cases,
- architecture decisions can be traced to concrete requirements,
- future changes can be made without ambiguity.

This document describes functional behavior only. Detailed technical implementation belongs in the architecture and system-design documents.

---

# 2. Functional Requirement Identification

Requirements use the following identifiers:

```text
FR-AUTH-xxx     Authentication
FR-SRC-xxx      Source management
FR-GMAIL-xxx    Gmail
FR-TOPIC-xxx   Topics
FR-EVENT-xxx   Event processing
FR-AI-xxx      AI processing
FR-DEDUP-xxx    Duplicate detection
FR-PRIO-xxx    Priority
FR-NOTIFY-xxx  Notifications
FR-ATT-xxx     Attachments
FR-HIST-xxx    History
FR-SEARCH-xxx  Search
FR-RULE-xxx    Rules
FR-UI-xxx      User interface
FR-SET-xxx     Settings
FR-ERR-xxx     Error handling
FR-LOG-xxx     Logging
FR-CONT-xxx    Content generation
FR-SYS-xxx     System/tray lifecycle
```

---

# 3. Functional Processing Model

Every incoming information item should follow this logical lifecycle:

```text
RECEIVED
   |
   v
IDENTIFIED
   |
   v
NORMALIZED
   |
   v
VALIDATED
   |
   v
DEDUPLICATED
   |
   v
CLASSIFIED
   |
   v
AI_PROCESSING
   |
   v
ANALYZED
   |
   v
PRIORITIZED
   |
   v
STORED
   |
   v
NOTIFIED
   |
   v
COMPLETED
```

Possible failure states:

```text
FAILED
RETRY_PENDING
IGNORED
DUPLICATE
```

The exact persistence model will be defined in the database design.

---

# 4. Application Lifecycle

## FR-SYS-001 — Application Startup

When the application starts it shall:

1. Load application configuration.
2. Initialize logging.
3. Initialize the local database.
4. Validate required configuration.
5. Load configured topics.
6. Load notification settings.
7. Initialize registered providers.
8. Restore authentication state where possible.
9. Initialize the system tray.
10. Initialize the UI.
11. Start the monitoring subsystem.
12. Display current connection and monitoring status.

The application must not block the UI while performing network or external-service initialization.

---

## FR-SYS-002 — Startup Failure

If one subsystem fails during startup:

- The entire application should not necessarily terminate.
- The failed subsystem shall report its state.
- The user shall be able to inspect the error.
- Other independent subsystems may continue operating.

Example:

```text
Gmail       Connected
Database    Connected
AI          Authentication Required
Notifications  Ready
```

---

## FR-SYS-003 — Graceful Shutdown

When the user exits the application:

1. Stop accepting new work.
2. Allow safe in-progress operations to finish where practical.
3. Persist required state.
4. Stop background workers.
5. Close provider connections.
6. Close the database cleanly.
7. Shut down the UI.

The application must not intentionally terminate active processing in a way that corrupts persistent state.

---

# 5. Authentication

## FR-AUTH-001 — Gmail OAuth

The user shall be able to connect a Gmail account using Google OAuth.

The application shall not ask the user to enter or store their Gmail password.

---

## FR-AUTH-002 — Authentication Status

The UI shall display:

```text
Not Connected
Connecting
Connected
Authorization Required
Connection Error
```

The status must be understandable without reading application logs.

---

## FR-AUTH-003 — Disconnect Gmail

The user shall be able to disconnect Gmail.

Disconnecting shall:

- Stop Gmail monitoring.
- Remove active monitoring subscriptions where applicable.
- Remove locally stored authentication material according to the security design.
- Preserve unrelated application data unless the user explicitly requests deletion.

---

## FR-AUTH-004 — Reauthorization

If authorization expires or is revoked:

1. Monitoring shall enter a degraded/disconnected state.
2. The user shall be notified.
3. The application shall provide a reauthorization action.
4. Existing processed history shall remain available.

---

# 6. Source Management

## FR-SRC-001 — Source Abstraction

The application shall represent external information sources through a common source abstraction.

Initial source:

```text
Gmail
```

Future sources may include:

```text
RSS
News API
Web
YouTube
Outlook
Telegram
Local Files
Other APIs
```

The user interface should represent sources generically wherever practical.

---

## FR-SRC-002 — Source Status

Each configured source shall expose a status:

```text
Connected
Disconnected
Connecting
Error
Paused
Not Configured
```

---

# 7. Gmail Functional Requirements

## FR-GMAIL-001 — Retrieve Gmail Labels

The application shall retrieve available Gmail labels after authentication.

The user shall be able to select labels for monitoring.

---

## FR-GMAIL-002 — Monitor Label

The user shall be able to enable monitoring for a specific Gmail label.

Example:

```text
TRUMP
IRAN
MODI
NIFTY
CELEBRITY_X
```

Monitoring one label shall not require monitoring all Gmail messages.

---

## FR-GMAIL-003 — Gmail Push Monitoring

The application shall use Gmail push notification/watch mechanisms as the primary real-time monitoring approach.

The system shall not depend on a fixed 30/60-second polling loop under normal operating conditions.

---

## FR-GMAIL-004 — Push Event Handling

When a Gmail change notification arrives:

1. Validate the event.
2. Determine the affected mailbox state.
3. Retrieve the relevant Gmail message/change information.
4. Determine whether the message belongs to a monitored label/topic.
5. Ignore unrelated information.
6. Continue the processing pipeline for relevant information.

---

## FR-GMAIL-005 — Push Event Duplication

The same external event may be delivered more than once.

The application shall handle repeated notifications safely.

Repeated delivery must not automatically result in repeated processing.

---

## FR-GMAIL-006 — Gmail Message Retrieval

For a relevant message, retrieve where available:

```text
Message ID
Thread ID
Sender
Recipients
Subject
Date/time
Labels
Plain text
HTML
Snippet
Attachments
Gmail URL
```

---

## FR-GMAIL-007 — Gmail Thread Handling

The system shall retain Gmail thread identifiers.

The initial processing model may process messages individually while preserving thread relationships.

Future versions may summarize entire threads.

---

## FR-GMAIL-008 — Gmail URL

Where possible, the application shall provide an action to open the original Gmail message.

---

# 8. Topic Management

## FR-TOPIC-001 — Create Topic

The user shall be able to create a topic with at least:

```text
Name
Description
Source
Source Identifier
AI Profile
AI Instructions
Priority
Notification Policy
Attachment Policy
Content Policy
Enabled/Disabled
```

---

## FR-TOPIC-002 — Edit Topic

The user shall be able to modify an existing topic without modifying application code.

---

## FR-TOPIC-003 — Delete Topic

The user shall be able to disable or delete a topic.

Deleting a topic must not automatically delete historical processed information unless explicitly requested.

---

## FR-TOPIC-004 — Enable/Disable Topic

A topic can be temporarily disabled.

Disabled topics shall not generate new processing or notifications.

Existing history remains available.

---

## FR-TOPIC-005 — Multiple Topics

The application shall support multiple topics simultaneously.

Example:

```text
TRUMP
IRAN
MODI
RBI
FED
NIFTY
CELEBRITY_X
AWS
OPENAI
```

---

## FR-TOPIC-006 — Topic Isolation

Changing one topic's AI prompt or notification configuration must not modify another topic.

---

# 9. AI Profile Management

## FR-AI-001 — AI Profile

An AI profile shall define how information is analyzed.

A profile may contain:

```text
Name
Purpose
System Instructions
Output Schema
Maximum Summary Length
Analysis Sections
Priority Rules
Confidence Rules
```

---

## FR-AI-002 — Default Profile

The application shall provide a general-purpose default AI profile.

Example behavior:

```text
Summarize the event.
Identify what changed.
Identify important entities.
Explain why it matters.
Identify uncertainty.
```

---

## FR-AI-003 — Custom Profile

The user shall be able to create custom profiles.

Example:

```text
Trading / Geopolitics
Entertainment
Technology
Finance
General News
```

---

## FR-AI-004 — Topic-to-Profile Mapping

A topic shall reference an AI profile.

Multiple topics may use the same profile.

Example:

```text
TRUMP      -> Trading / Geopolitics
IRAN       -> Trading / Geopolitics
MODI       -> Trading / India
CELEBRITY  -> Entertainment
AWS        -> Technology
```

---

## FR-AI-005 — Prompt Version

The system shall record which AI prompt/profile version was used to process an item.

This is important because AI output may differ after a prompt changes.

---

# 10. Email Normalization

## FR-EVENT-001 — Common Event

Incoming Gmail information shall be converted into a provider-independent internal event/document representation.

At minimum the common representation should contain:

```text
External ID
Source
Source Account
Timestamp
Title/Subject
Author/Sender
Content
Labels
Attachments
Source URL
Raw Metadata
```

---

## FR-EVENT-002 — Content Extraction

The application shall prefer readable text for AI processing.

HTML emails shall be converted into clean text while preserving meaningful information.

Tracking pixels, irrelevant markup, and unnecessary formatting should be removed where practical.

---

## FR-EVENT-003 — Empty Content

If an email contains insufficient readable content:

- The system shall record the condition.
- AI processing may be skipped or use available metadata.
- The user should receive an appropriate status rather than a misleading summary.

---

# 11. Deduplication

## FR-DEDUP-001 — Exact Duplicate

The system shall detect the same external message ID when possible.

---

## FR-DEDUP-002 — Content Duplicate

The system should support detection of substantially identical content even when external IDs differ.

---

## FR-DEDUP-003 — Similar Story

The system should eventually identify articles/events that refer to the same underlying development.

Example:

```text
Trump announces policy
Trump makes statement
Trump warns Iran
Trump issues new warning
```

These may represent one evolving story.

---

## FR-DEDUP-004 — Duplicate Action

For duplicate information:

- Preserve the source record where appropriate.
- Avoid unnecessary duplicate AI processing.
- Avoid repeated high-priority notifications.
- Maintain references between duplicates.

---

# 12. AI Processing

## FR-AI-010 — Mandatory Summary

Every eligible incoming item shall receive an AI summary.

The summary shall be concise enough for desktop notification use while preserving important facts.

---

## FR-AI-011 — Structured Analysis

The AI processing result should support structured fields such as:

```text
Headline
Summary
Key Facts
Entities
Event
Importance
Priority
Confidence
Uncertainty
Topic Analysis
Potential Impact
Follow-up
```

---

## FR-AI-012 — Fact vs Interpretation

Where practical, AI output should distinguish:

```text
Confirmed Facts
AI Interpretation
Potential Implications
Uncertainty
```

This is especially important for financial and geopolitical information.

---

## FR-AI-013 — Trading Analysis

If enabled for a topic, AI may analyze:

```text
Potential Market Impact
Affected Assets
Potential Bias
Risk
Confidence
Key Levels/Events to Watch
```

The system must label this as AI analysis, not guaranteed prediction.

---

## FR-AI-014 — Topic-Specific Output

If a topic does not request trading analysis, the AI shall not generate trading analysis merely because the content happens to mention markets.

---

## FR-AI-015 — AI Failure

If AI processing fails:

1. Record the failure.
2. Retry when appropriate.
3. Do not lose the source event.
4. Show an appropriate processing status.
5. Allow manual retry.

The application must not fabricate a summary when AI processing fails.

---

## FR-AI-016 — AI Provider Timeout

A timeout shall be treated as a recoverable processing failure unless classified otherwise.

---

## FR-AI-017 — Invalid AI Output

If the AI returns malformed structured output:

1. Validate it.
2. Attempt controlled recovery if supported.
3. Retry if appropriate.
4. Record the failure.
5. Never silently store invalid data as valid intelligence.

---

# 13. Priority

## FR-PRIO-001 — Priority Levels

Supported levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

## FR-PRIO-002 — Priority Sources

Priority may be determined from:

- Topic configuration.
- AI analysis.
- Rules.
- Event characteristics.
- User-defined thresholds.

---

## FR-PRIO-003 — Priority Override

The user may configure a minimum notification priority.

Example:

```text
Topic: TRUMP

LOW      -> Store
MEDIUM   -> Store
HIGH     -> Notify
CRITICAL -> Notify + Sound
```

---

# 14. Notifications

## FR-NOTIFY-001 — Notification Creation

When an eligible event reaches the notification stage, the application shall create a desktop notification.

---

## FR-NOTIFY-002 — Notification Content

A notification may include:

```text
Priority
Topic
Headline
AI Summary
Important Impact
Timestamp
Actions
```

The notification should not expose excessive raw email content.

---

## FR-NOTIFY-003 — Notification Animation

The Windows popup shall:

1. Appear near the bottom-right of the desktop.
2. Animate into view.
3. Remain visible for configured duration.
4. Fade out.
5. Close cleanly.

---

## FR-NOTIFY-004 — Notification Actions

Supported actions should include:

```text
Open Original
View Details
Dismiss
```

Future actions may include:

```text
Generate Video
Mark Important
Mute Topic
Open Story
```

---

## FR-NOTIFY-005 — Notification Queue

If multiple events arrive together:

- Notifications shall be queued or stacked.
- The UI must remain responsive.
- Notifications must not overlap in an unusable way.

---

## FR-NOTIFY-006 — Quiet Hours

The user may configure quiet hours.

During quiet hours:

- Events continue to be processed and stored.
- Notifications may be suppressed.
- High/critical events may optionally bypass quiet hours.

---

## FR-NOTIFY-007 — Notification History

The application shall maintain notification history.

The user shall be able to see which notifications were:

```text
Displayed
Dismissed
Opened
Suppressed
Failed
```

---

# 15. Attachment Processing

## FR-ATT-001 — Attachment Discovery

The system shall identify attachments associated with an email.

Metadata should include:

```text
Filename
MIME Type
Size
Attachment ID
```

---

## FR-ATT-002 — Download Policy

The user shall be able to enable or disable downloading.

```text
Download = ON
Download = OFF
```

---

## FR-ATT-003 — Attachment Type Rules

The user should be able to configure permitted types.

Example:

```text
PDF   -> Yes
XLSX  -> Yes
CSV   -> Yes
ZIP   -> No
JPG   -> No
```

---

## FR-ATT-004 — Attachment Size Rules

The user should be able to define a maximum attachment size for automatic processing/download.

---

## FR-ATT-005 — Attachment Processing

If enabled, the application may extract useful content from supported attachments and provide it to the AI pipeline.

---

## FR-ATT-006 — Attachment Failure

An attachment failure shall not cause the entire email processing operation to fail unless the configured workflow explicitly requires the attachment.

Example:

```text
Email summary -> Successful
PDF extraction -> Failed
Overall email -> Completed with warning
```

---

## FR-ATT-007 — Archive Handling

ZIP files shall not be automatically extracted unless explicitly enabled by the user.

Archive processing must include security validation to prevent unsafe extraction behavior.

---

# 16. History

## FR-HIST-001 — Store Processed Event

The application shall store successfully processed events.

---

## FR-HIST-002 — Processing Metadata

History shall preserve:

```text
Source
External ID
Topic
Received Time
Processed Time
AI Provider
AI Model
AI Profile
Prompt Version
Priority
Processing Status
```

---

## FR-HIST-003 — Original Content

The application should retain the original email content or a controlled representation according to the configured data-retention policy.

---

## FR-HIST-004 — AI Output

The generated AI summary and structured analysis shall be persisted.

---

# 17. Search

## FR-SEARCH-001 — Basic Search

The user shall be able to search:

```text
Subject
Sender
Topic
Label
Summary
Entity
Keyword
```

---

## FR-SEARCH-002 — Filters

The user shall be able to filter by:

```text
Date
Topic
Priority
Source
Processing Status
Has Attachment
Notification Status
```

---

## FR-SEARCH-003 — Full-Text Search

The initial implementation should support efficient local full-text search.

---

## FR-SEARCH-004 — Natural Language Search

Natural-language search is a future capability.

Example:

```text
Show all high-impact Iran developments from this week.
```

---

# 18. Story and Timeline

## FR-HIST-010 — Story

A story represents a collection of related events.

Example:

```text
Iran-US Negotiations

Event 1
Event 2
Event 3
Event 4
```

---

## FR-HIST-011 — Timeline

A story view should eventually display events chronologically.

---

## FR-HIST-012 — Story Summary

The system should eventually maintain an evolving AI-generated summary of a story.

This summary should be updated when significant new events arrive.

---

# 19. Rules

## FR-RULE-001 — Rule Definition

Users shall eventually be able to define conditional actions.

Conceptual model:

```text
WHEN condition
IF condition
THEN action
```

Example:

```text
WHEN new item arrives
IF topic = TRUMP
AND priority >= HIGH
THEN notify
```

---

## FR-RULE-002 — Rule Actions

Potential actions:

```text
Notify
Store
Suppress
Generate AI analysis
Download attachment
Generate YouTube script
Generate video
```

---

## FR-RULE-003 — Rule Evaluation

Rules must be evaluated in a deterministic and auditable manner.

The system should record which rule caused an action.

---

# 20. User Interface

## FR-UI-001 — Dashboard

The dashboard shall show high-level application status.

---

## FR-UI-002 — Topic List

The topic screen shall allow:

- View topics.
- Create topic.
- Edit topic.
- Enable/disable topic.
- Delete topic.

---

## FR-UI-003 — Live Feed

The live feed shall display newly processed items.

Suggested information:

```text
Time
Topic
Headline
Priority
AI Summary
Status
```

---

## FR-UI-004 — Detail View

Selecting an event shall display:

```text
Original Information
AI Summary
AI Analysis
Entities
Priority
Attachments
Processing History
Source Link
```

---

## FR-UI-005 — Processing Status

The UI shall clearly show processing states.

Example:

```text
Received
Processing
AI Analysis
Completed
Failed
Retrying
Duplicate
Ignored
```

---

# 21. System Tray

## FR-SYS-010 — Tray Icon

The application shall provide a system-tray icon.

---

## FR-SYS-011 — Tray Menu

The menu shall provide:

```text
Open
Pause Monitoring
Resume Monitoring
Topics
Notifications
Settings
Logs
About
Exit
```

---

## FR-SYS-012 — Pause Monitoring

When monitoring is paused:

- New source events may continue to exist externally.
- InsightFlow should not actively process them according to the configured pause semantics.
- The UI must clearly indicate that monitoring is paused.

The exact catch-up behavior shall be configurable in the system design.

---

# 22. Settings

## FR-SET-001 — General Settings

General settings shall include:

- Start with Windows.
- Minimize to tray.
- Theme.
- Language where supported.
- Data directory.

---

## FR-SET-002 — Notification Settings

Include:

```text
Enabled
Sound
Duration
Animation
Minimum Priority
Quiet Hours
```

---

## FR-SET-003 — AI Settings

Include:

```text
Provider
Model
Temperature/creativity where supported
Timeout
Retry
Default Profile
```

---

## FR-SET-004 — Attachment Settings

Include:

```text
Download enabled
Allowed types
Maximum size
Download directory
Processing enabled
```

---

## FR-SET-005 — Retention Settings

The user should eventually be able to configure how long:

- Raw email content.
- AI summaries.
- Attachments.
- Logs.

are retained.

---

# 23. Logging

## FR-LOG-001 — Application Log

The application shall record significant lifecycle events.

---

## FR-LOG-002 — Processing Log

Each event should have enough information to reconstruct the processing lifecycle.

---

## FR-LOG-003 — Sensitive Data

Logs must not contain passwords, OAuth tokens, API keys, or unnecessary email content.

---

# 24. Error Handling

## FR-ERR-001 — User-Friendly Errors

Technical errors shall be converted into understandable UI messages where possible.

Example:

Instead of:

```text
HTTP 401
```

show:

```text
Gmail authorization has expired.
Please reconnect your Google account.
```

Detailed technical information remains available in logs.

---

## FR-ERR-002 — Retry

Retryable errors shall support automatic retry where safe.

---

## FR-ERR-003 — Manual Retry

The user shall be able to retry failed processing from the detail/history screen.

---

## FR-ERR-004 — No Silent Loss

An external event that cannot be processed must remain visible in an error or pending state.

---

# 25. Content Generation — Future Functional Requirements

## FR-CONT-001 — Generate YouTube Script

A selected story/event shall eventually be convertible into a YouTube script.

---

## FR-CONT-002 — Target Duration

The user shall be able to select a target duration.

Initial target:

```text
Approximately 3 minutes
```

---

## FR-CONT-003 — Script Sections

A generated script should support:

```text
Hook
Introduction
Main Facts
Context
Why It Matters
Latest Development
What To Watch
Conclusion
Call To Action
```

Sections may vary by topic/profile.

---

## FR-CONT-004 — Script Regeneration

The user shall be able to regenerate or edit a script.

---

## FR-CONT-005 — Video Pipeline

Future pipeline:

```text
Story
  |
  v
Script
  |
  v
Voice
  |
  v
Visual Assets
  |
  v
Video Composition
  |
  v
Thumbnail
  |
  v
Metadata
  |
  v
Approval
  |
  v
YouTube
```

---

# 26. YouTube Publishing — Future

## FR-CONT-010

The system shall eventually support:

- YouTube OAuth.
- Video upload.
- Title.
- Description.
- Tags.
- Thumbnail.
- Privacy status.
- Scheduled publishing.

Initial publishing must require user approval.

---

# 27. Auditability

## FR-SYS-020

The application should maintain an audit trail for important actions.

Examples:

```text
Topic Created
Topic Changed
Prompt Changed
Gmail Connected
Gmail Disconnected
Event Processed
AI Analysis Generated
Notification Displayed
Attachment Downloaded
Content Generated
Video Published
```

---

# 28. Data Consistency

## FR-SYS-030

The system shall maintain consistent processing state.

Example:

```text
Email received
      |
      v
Database record created
      |
      v
AI processing
      |
      v
Result saved
      |
      v
Notification created
```

A crash between steps must not leave the database claiming an operation succeeded when it did not.

---

# 29. Processing Recovery

## FR-SYS-031

After application restart, the system shall identify unfinished operations where possible.

Example:

```text
Status = AI_PROCESSING
```

The application may transition it to:

```text
RETRY_PENDING
```

and safely retry.

---

# 30. Configuration Export/Import

## FR-SET-010 — Future/Recommended

The application should eventually support exporting non-secret configuration.

Example:

```text
Topics
AI Profiles
Rules
Notification Preferences
```

Secrets/tokens must never be exported in plain text.

---

# 31. Backup

## FR-SYS-040 — Recommended

The application should support backup of:

- Database.
- Topic configuration.
- AI profiles.
- Rules.
- Non-secret settings.

Attachment backup may be handled separately because of potentially large file sizes.

---

# 32. End-to-End Functional Flow

The minimum complete functional flow is:

```text
1. User starts InsightFlow
        |
2. Gmail authenticated
        |
3. User configures topic
        |
4. User selects Gmail label
        |
5. Gmail push monitoring active
        |
6. Google Alert arrives
        |
7. Gmail generates change notification
        |
8. InsightFlow receives event
        |
9. Relevant message identified
        |
10. Message retrieved
        |
11. Content normalized
        |
12. Duplicate check
        |
13. Topic/profile resolved
        |
14. AI processing
        |
15. AI output validated
        |
16. Priority determined
        |
17. Result persisted
        |
18. Notification generated
        |
19. User sees popup
        |
20. User can open details/source
```

---

# 33. Functional State Model

An incoming item should support states similar to:

```text
RECEIVED
   |
IDENTIFIED
   |
NORMALIZED
   |
VALIDATED
   |
DEDUPLICATED
   |
CLASSIFIED
   |
AI_PENDING
   |
AI_PROCESSING
   |
AI_COMPLETED
   |
STORED
   |
NOTIFICATION_PENDING
   |
NOTIFIED
   |
COMPLETED
```

Alternative paths:

```text
DUPLICATE
IGNORED
RETRY_PENDING
FAILED
```

The exact state machine and transition rules belong in the system design document.

---

# 34. Functional Boundaries

The following responsibilities must remain separate:

```text
Gmail Adapter
    -> Gmail communication only

Source Normalizer
    -> Common event representation

Topic Resolver
    -> Determines applicable topic/profile

AI Service
    -> AI interaction

AI Output Validator
    -> Validates structured AI response

Priority Engine
    -> Determines priority

Notification Service
    -> Desktop notification

Attachment Service
    -> Attachment handling

Persistence
    -> Database operations

Workflow Engine
    -> Conditional actions

UI
    -> Presentation and user interaction
```

No component should silently take ownership of unrelated responsibilities.

---

# 35. Important Functional Constraints

The implementation must respect the following:

1. No topic-specific source code.
2. No AI prompt hardcoded into domain logic.
3. No Gmail API calls directly from UI code.
4. No database queries directly from UI widgets.
5. No long-running AI/network work on the UI thread.
6. No automatic attachment download unless enabled.
7. No automatic YouTube publishing in the initial version.
8. No fabricated AI summary when AI processing fails.
9. No duplicate processing caused by duplicate external notifications.
10. No silent loss of unprocessed events.

---

# 36. Definition of Functional Completion

A functional requirement is considered complete only when:

- The expected behavior is implemented.
- Success behavior is tested.
- Failure behavior is tested.
- Relevant configuration is exposed.
- Logging exists for important operations.
- The UI communicates meaningful status.
- Existing functionality remains operational.
- Documentation is updated.
- The requirement can be traced to tests.

---

# 37. MVP Functional Checklist

The first implementation must demonstrate all of the following:

```text
[ ] Gmail OAuth
[ ] Gmail label discovery
[ ] Gmail label selection
[ ] Gmail label monitoring
[ ] Gmail push/watch mechanism
[ ] Event retrieval
[ ] Email normalization
[ ] Duplicate protection
[ ] Topic resolution
[ ] AI profile selection
[ ] AI summary
[ ] Structured AI output
[ ] Priority
[ ] Local persistence
[ ] Desktop popup
[ ] Notification actions
[ ] System tray
[ ] History
[ ] Basic search
[ ] Attachment discovery
[ ] Optional attachment download
[ ] Error handling
[ ] Retry
[ ] Logging
[ ] Settings
[ ] Clean shutdown
[ ] Recovery after restart
```

---

# 38. Future Functional Checklist

```text
[ ] Story grouping
[ ] Story timeline
[ ] AI chat
[ ] Natural-language search
[ ] Multiple source providers
[ ] Multiple AI providers
[ ] Advanced rules engine
[ ] YouTube script generation
[ ] Three-minute video generation
[ ] Text-to-speech
[ ] Image generation
[ ] Video composition
[ ] Thumbnail generation
[ ] YouTube upload
[ ] Scheduled publishing
[ ] Additional publishing channels
```

---

# 39. Requirement Governance

Functional requirements must remain aligned with:

```text
00_Project_Vision.md
01_Product_Requirements.md
02_Functional_Requirements.md
```

If a feature request conflicts with an existing requirement:

1. Identify the conflict.
2. Discuss the intended product behavior.
3. Update the relevant requirement.
4. Update dependent design documents.
5. Update tests.
6. Record the change when architecturally significant.

AI coding agents must not silently reinterpret functional requirements.

---

# 40. Final Functional Principle

InsightFlow AI shall provide a configurable pipeline in which:

```text
USER INTENT
    +
SOURCE INFORMATION
    +
CONFIGURED AI BEHAVIOR
    +
PROCESSING RULES
    =
PERSONALIZED INTELLIGENCE
```

The application must remain generic enough that adding a new topic such as a celebrity, politician, company, technology product, geopolitical event, market subject, or any other information category requires configuration rather than new application code.
