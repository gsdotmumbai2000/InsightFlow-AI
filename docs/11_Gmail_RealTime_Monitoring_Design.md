# InsightFlow AI — Gmail Real-Time Monitoring Design

**Document:** `11_Gmail_RealTime_Monitoring_Design.md`  
**Status:** Draft / Foundational Technical Design  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `04_System_Architecture.md`, `05_System_Design.md`, `06_Database_Design.md`, `10_Interface_and_API_Contracts.md`

---

# 1. Purpose

This document defines the technical design for monitoring Gmail labels in near-real-time and converting matching Gmail activity into InsightFlow AI intelligence events.

The primary requirement is:

> **Do not repeatedly poll Gmail every 30 or 60 seconds. Use Gmail's change-notification mechanism so the application reacts when Gmail reports that the mailbox has changed.**

The target flow is:

```text
Google Alert / Email Source
        |
        v
Gmail Label
        |
        v
Gmail Mailbox Change
        |
        v
Gmail Watch
        |
        v
Google Cloud Pub/Sub
        |
        v
InsightFlow Subscriber
        |
        v
History ID
        |
        v
Gmail History API
        |
        v
Changed Message IDs
        |
        v
Gmail Message API
        |
        v
Label / Topic Filtering
        |
        v
NormalizedSourceEvent
        |
        v
InsightFlow Processing Pipeline
        |
        +--> Database
        +--> AI Summary
        +--> Priority / Impact
        +--> Windows Notification
        +--> Attachment Processing
```

---

# 2. Important Terminology

## 2.1 Gmail Label

A Gmail label identifies messages belonging to a monitoring category.

Examples:

```text
Google Alerts/Trump
Google Alerts/Iran
Google Alerts/US Market
Google Alerts/Modi
Google Alerts/Celebrity X
```

The actual user's labels are configurable.

The application must never hardcode specific news subjects.

---

## 2.2 Gmail Watch

A Gmail watch requests Gmail to send mailbox-change notifications through Google Cloud Pub/Sub.

The notification indicates that the mailbox changed.

It does not necessarily contain the complete email message.

---

## 2.3 History ID

Gmail uses a mailbox history identifier to allow the application to determine what changed since a known point.

The application should persist the latest successfully processed history position.

---

## 2.4 Pub/Sub

Google Cloud Pub/Sub delivers Gmail change notifications to the configured subscriber.

Pub/Sub is the real-time trigger mechanism.

---

# 3. Core Requirement

The system must NOT use:

```text
while True:
    check Gmail
    sleep(30)
```

or:

```text
check every 60 seconds
```

as the primary real-time architecture.

Instead:

```text
Gmail
   |
   v
Watch
   |
   v
Pub/Sub
   |
   v
Application
```

Polling may exist only as a recovery/reconciliation mechanism if explicitly required.

---

# 4. Why Push Notification Is Used

Polling creates:

```text
Unnecessary API calls
Latency
Rate-limit pressure
Poor scalability
Battery/CPU usage
Delayed alerts
```

Push notification provides:

```text
Lower latency
Lower unnecessary API usage
Event-driven architecture
Better real-time behavior
```

There may still be unavoidable processing latency caused by:

```text
Pub/Sub delivery
Gmail history retrieval
AI processing
Database writes
```

Therefore the application should describe the feature as:

> **Real-time / event-driven monitoring**

rather than promising zero-millisecond delivery.

---

# 5. Monitoring Scope

The application monitors:

```text
One or more Gmail labels
```

for a configured Gmail account.

A user may configure:

```text
Topic A -> Label A
Topic B -> Label B
Topic C -> Label C
```

Example:

```text
Trump
   -> Google Alerts/Trump

Iran-US
   -> Google Alerts/Iran-US

US Market
   -> Google Alerts/US Market

Celebrity X
   -> Google Alerts/Celebrity X
```

---

# 6. Important Design Decision — Labels Are Configuration

The application must NOT contain:

```python
if "Trump" in subject:
    ...
```

or:

```python
if label == "Iran":
    ...
```

Instead:

```text
Gmail Label
       |
       v
Topic Configuration
       |
       v
AI Profile
       |
       v
Notification Policy
```

---

# 7. Topic Configuration Example

Conceptually:

```text
Topic
------------------------------------------------
Name: Trump
Enabled: Yes
Gmail Label: Google Alerts/Trump
AI Profile: Trading/Geopolitics
Notification Policy: High Impact
Attachments: Optional
```

Another:

```text
Topic
------------------------------------------------
Name: Celebrity X
Enabled: Yes
Gmail Label: Google Alerts/Celebrity X
AI Profile: Entertainment
Notification Policy: Normal
Attachments: Disabled
```

Same processing engine.

Different configuration.

---

# 8. Google Cloud Components

The real-time architecture requires Google-side infrastructure for the Gmail watch notification path.

Conceptually:

```text
Google Account
      |
      v
Gmail API
      |
      v
Gmail Watch
      |
      v
Google Cloud Pub/Sub Topic
      |
      v
Pub/Sub Subscription
      |
      v
InsightFlow Subscriber
```

The exact Google Cloud project setup must be documented during implementation.

---

# 9. OAuth Architecture

The application requires Gmail authorization.

The OAuth flow should obtain the minimum required Gmail permissions.

The exact scopes must be reviewed before implementation and should follow Google's current Gmail API requirements.

Potential capabilities include:

```text
Read messages
Read labels
Read mailbox history
Manage watch where required
```

Do not request broad Gmail permissions unless necessary.

---

# 10. Credential Storage

OAuth refresh credentials must not be stored in:

```text
Source code
Plain text project files
Git
Logs
SQLite event tables
```

Preferred Windows storage:

```text
Windows Credential Manager / secure OS credential mechanism
```

The application stores only non-secret metadata in ordinary configuration/database storage.

---

# 11. OAuth Token Lifecycle

Conceptual:

```text
Application
    |
    v
Secure credential store
    |
    v
Access token
    |
    v
Gmail API
```

The application should allow:

```text
Connect
Reconnect
Disconnect
Reauthorize
```

---

# 12. Gmail Connection States

Recommended states:

```text
DISCONNECTED
AUTHENTICATING
CONNECTED
WATCH_STARTING
WATCH_ACTIVE
WATCH_RENEWING
RECONNECTING
AUTH_ERROR
ERROR
STOPPED
```

---

# 13. Monitoring Lifecycle

Startup:

```text
Application Start
      |
      v
Load Gmail configuration
      |
      v
Load credentials
      |
      v
Validate Gmail access
      |
      v
Validate monitored labels
      |
      v
Start / renew watch
      |
      v
Start Pub/Sub subscriber
      |
      v
WATCH_ACTIVE
```

---

# 14. Monitoring Shutdown

Graceful shutdown:

```text
Stop accepting new notifications
        |
        v
Stop subscriber
        |
        v
Finish/acknowledge safe in-flight work
        |
        v
Persist state
        |
        v
Close resources
        |
        v
Application exit
```

---

# 15. Gmail Watch Renewal

Gmail watch registrations are not permanent.

The application must track:

```text
watch_started_at
watch_expiration
```

and renew the watch before expiration.

Do not wait until the watch has already expired.

---

# 16. Renewal Strategy

Conceptually:

```text
Watch expiration
      |
      v
Renewal threshold
      |
      v
Renew watch
      |
      v
Persist new expiration
```

The exact renewal interval must be based on the current Gmail API behavior and validated during implementation.

---

# 17. Renewal Failure

If renewal fails:

```text
Retry according to retry policy.
```

If repeated renewal attempts fail:

```text
Monitoring status = ERROR
```

The application should notify the user through the UI/system tray.

---

# 18. Pub/Sub Message

The Gmail watch notification is expected to identify the Gmail account and a history position.

Conceptually:

```json
{
  "emailAddress": "account@example.com",
  "historyId": "123456"
}
```

The exact payload must be treated according to the current Gmail API specification.

---

# 19. Important Rule

The Pub/Sub notification should NOT be treated as the email itself.

It is a:

```text
Change notification
```

The application must use the history information to determine what changed.

---

# 20. Pub/Sub Subscription

The application consumes from a configured Pub/Sub subscription.

Conceptually:

```text
Gmail
  |
  v
Pub/Sub Topic
  |
  v
Subscription
  |
  v
InsightFlow Subscriber
```

---

# 21. Subscriber Architecture

Recommended:

```text
PubSubSubscriber
      |
      v
PubSubMessageParser
      |
      v
GmailChangeNotification
      |
      v
GmailHistoryProcessor
```

---

# 22. Pub/Sub Acknowledgement

The application must acknowledge a Pub/Sub message only after it has decided that processing is safely complete according to the delivery policy.

The acknowledgement strategy must prevent silent loss.

---

# 23. Acknowledgement Principle

Bad:

```text
Receive Pub/Sub message
    |
    v
Immediately ACK
    |
    v
Process later
```

A process crash after ACK may lose the notification.

Preferred:

```text
Receive
   |
   v
Validate
   |
   v
Process/persist required state
   |
   v
ACK
```

The exact boundary must be designed together with idempotent processing.

---

# 24. Duplicate Pub/Sub Delivery

Pub/Sub delivery may be repeated.

Example:

```text
Notification A
Notification A
```

The system must tolerate duplicates.

Do not assume:

```text
one Pub/Sub message = one email
```

---

# 25. History ID Processing

Conceptual flow:

```text
Pub/Sub historyId = H2
       |
       v
Load last processed history position = H1
       |
       v
Gmail history.list(H1)
       |
       v
Changed messages
       |
       v
Process messages
       |
       v
Persist progress
```

---

# 26. Important History Rule

The application must understand that Gmail history represents mailbox changes, not simply a list of new emails.

Changes may include:

```text
Message added
Label added
Label removed
Message deleted
```

The application must process only the changes relevant to configured monitoring behavior.

---

# 27. New Message Detection

For monitored topics, a message is relevant when the message acquires the configured monitored label or otherwise satisfies the configured source rule.

The implementation must not rely only on:

```text
internalDate > lastCheck
```

because real-time correctness depends on mailbox history/change semantics.

---

# 28. Label Filtering

The application should first load Gmail label metadata.

Example:

```text
Label ID
Label Name
```

Then map:

```text
Gmail Label ID
      |
      v
Topic ID
```

---

# 29. Label ID vs Label Name

Use Gmail's stable label ID internally where possible.

Store/display:

```text
label_id
label_name
```

The user interface displays the human-readable name.

---

# 30. Label Mapping

Recommended table/concept:

```text
Topic
    |
    +-- source_type = GMAIL
    +-- gmail_account_id
    +-- gmail_label_id
    +-- gmail_label_name_snapshot
```

The ID is authoritative.

The name is useful for display/diagnostics.

---

# 31. Label Discovery

The UI should allow:

```text
Connect Gmail
      |
      v
Load labels
      |
      v
Display selectable labels
      |
      v
User selects label
      |
      v
Create/update topic
```

---

# 32. Label Refresh

The application should provide:

```text
Refresh Gmail Labels
```

because users may create new labels in Gmail after configuring InsightFlow.

---

# 33. Missing Label

If a configured label no longer exists:

```text
Topic status = SOURCE_CONFIGURATION_ERROR
```

Monitoring for other valid labels should continue if possible.

---

# 34. Label Rename

If Gmail retains the same label ID while the display name changes, the application should refresh the stored display name.

The topic identity remains associated with the label ID.

---

# 35. Message Retrieval

After detecting a relevant changed message:

```text
Gmail History
     |
     v
Message ID
     |
     v
Gmail Messages.get
     |
     v
Raw Gmail Message
```

---

# 36. Message Normalization

The Gmail adapter converts the provider response into:

```text
NormalizedSourceEvent
```

The application should not process Gmail's raw nested JSON directly.

---

# 37. Message Content Extraction

The adapter should extract, where available:

```text
From
To
Cc
Subject
Date
Plain text
HTML
Snippet
Message ID
Thread ID
Labels
Attachments
Source URL/reference
```

---

# 38. HTML Handling

HTML email content is untrusted.

The application must:

```text
Sanitize
Normalize
Strip dangerous scripts
```

before rendering or sending to downstream components as appropriate.

---

# 39. Plain Text Preference

For AI processing:

```text
Plain text
```

should generally be preferred.

If only HTML exists:

```text
Sanitized HTML -> text extraction -> AI
```

---

# 40. Google Alert Example

A typical monitored flow may be:

```text
Google Alert
     |
     v
Gmail Inbox
     |
     v
User label:
Google Alerts/Trump
     |
     v
Gmail Watch
     |
     v
Pub/Sub
     |
     v
InsightFlow
     |
     v
Topic = Trump
     |
     v
AI Profile = Trading/Geopolitics
```

No code knows that "Trump" is special.

---

# 41. Multiple Topics

One Gmail account may have:

```text
Label A -> Topic A
Label B -> Topic B
Label C -> Topic C
Label D -> Topic D
```

The monitoring service must support all configured labels.

---

# 42. Multiple Gmail Accounts

Future architecture may support:

```text
Account A
    |
    +-- Topics

Account B
    |
    +-- Topics
```

The core event model should include a source/account identity where required.

MVP may support one Gmail account if that simplifies implementation.

---

# 43. Account Isolation

Messages from one configured Gmail account must not accidentally be associated with another account's topics.

---

# 44. Gmail Thread Handling

Google Alerts and newsletters may use threads.

The application must decide whether each relevant message is:

```text
A new intelligence event
```

or:

```text
An update to an existing event/story
```

The initial implementation should treat distinct newly relevant messages as separate intelligence events unless a deterministic deduplication/story rule combines them.

---

# 45. Thread ID

Store:

```text
gmail_thread_id
```

where available.

This supports:

```text
Investigation
Story grouping
Deduplication analysis
Source navigation
```

---

# 46. Duplicate Message Detection

Use stable identifiers such as:

```text
source account
+
Gmail message ID
```

to avoid creating duplicate intelligence events.

---

# 47. Duplicate Event Detection

Even if Gmail delivers the same message through multiple change records, the database uniqueness constraint should prevent duplicate intelligence events.

---

# 48. Processing Sequence

Recommended:

```text
1. Receive Pub/Sub notification
2. Parse notification
3. Validate Gmail account
4. Load last processed history state
5. Retrieve Gmail history changes
6. Identify relevant message IDs
7. Retrieve relevant messages
8. Determine monitored labels
9. Deduplicate
10. Normalize message
11. Create event
12. Persist event
13. Queue AI analysis
14. Persist processing progress
15. ACK Pub/Sub message
```

The exact transaction/ack boundary should be validated through failure testing.

---

# 49. Important Processing Principle

Do not make the Pub/Sub callback perform the entire AI workflow synchronously if that would cause acknowledgement deadlines or responsiveness problems.

Prefer:

```text
Pub/Sub callback
      |
      v
Validate + enqueue durable work
      |
      v
Worker
      |
      v
Full processing
```

where the queue/persistence design supports safe recovery.

---

# 50. Durable Work

The processing system should ensure that work is not lost if the application crashes.

Possible state:

```text
PROCESSING_PENDING
PROCESSING
COMPLETED
RETRY_PENDING
FAILED
```

---

# 51. Crash Scenario

Example:

```text
Pub/Sub notification received
       |
       v
Message identified
       |
       v
Application crashes
```

On restart, the system must be able to recover from persisted state/history rather than assuming the event never existed.

---

# 52. History Progress Persistence

Persist enough information to know:

```text
Gmail account
Last known history ID
Last successful synchronization time
Last watch expiration
```

---

# 53. History State Table

Conceptually:

```text
gmail_monitor_state
--------------------------------
id
account_id
last_history_id
watch_expiration
last_sync_at
last_success_at
last_error
status
updated_at
```

Exact schema is defined in the database design.

---

# 54. History Position Update

The application must not blindly advance the history position before processing required changes.

A crash between:

```text
advance history
```

and:

```text
persist event
```

could cause data loss.

---

# 55. Safe Progress Principle

The system should prefer:

```text
Duplicate processing
```

over:

```text
Lost processing
```

because duplicate processing can be controlled through idempotency.

---

# 56. History ID Gap

If the application is offline for a significant period, Gmail may no longer retain the required history.

The API may report that the requested history position is unavailable.

This must be treated as a synchronization recovery condition.

---

# 57. History Recovery

If history cannot be retrieved:

```text
Mark monitor state as RESYNC_REQUIRED
```

Then perform a controlled recovery.

Potential strategy:

```text
Fetch recent relevant messages
      |
      v
Deduplicate using Gmail message IDs
      |
      v
Rebuild current monitoring position
```

The exact recovery window should be configurable.

---

# 58. Resynchronization

Resync must be:

```text
Explicit
Observable
Idempotent
Bounded
```

The UI should show:

```text
Re-syncing Gmail...
```

rather than silently appearing connected.

---

# 59. Resync Notification

If resync is required, the user should receive a clear status indication.

Example:

```text
Gmail monitoring needs to resynchronize.
Some historical changes may need review.
```

---

# 60. Reconnection

Network failure:

```text
ACTIVE
  |
  v
ERROR
  |
  v
RECONNECTING
  |
  v
CONNECTED
  |
  v
WATCH_ACTIVE
```

---

# 61. Exponential Backoff

Reconnect operations should use bounded exponential backoff.

Conceptually:

```text
1s
2s
4s
8s
...
maximum
```

The exact values should be configuration-driven.

---

# 62. Jitter

Retry delays should include jitter where appropriate to avoid synchronized retry storms.

---

# 63. Authentication Failure

Authentication errors should not be retried forever.

Example:

```text
AUTH_ERROR
```

requires user action:

```text
Reconnect Google account
```

---

# 64. API Quota Failure

Quota/rate-limit errors are typically retryable according to provider guidance.

The application should:

```text
Back off
Limit concurrency
Retry
```

rather than repeatedly hammering Gmail.

---

# 65. Pub/Sub Failure

If Pub/Sub subscriber connection fails:

```text
Monitoring status = RECONNECTING
```

The application should reconnect.

---

# 66. Pub/Sub Message Expiration

If a message cannot be processed before acknowledgement deadline, the subscriber should extend/renew the lease where supported or allow redelivery rather than silently losing the message.

---

# 67. Poison Message

A malformed or permanently invalid message must not create an infinite retry loop.

Use:

```text
Dead-letter / failure handling
```

where appropriate.

---

# 68. Gmail API Timeout

A timeout should:

```text
Not crash the application
Be classified as retryable
Use bounded retry
Log correlation information
```

---

# 69. AI Failure Does Not Mean Gmail Failure

If:

```text
Gmail succeeded
AI failed
```

the Gmail event remains successfully received.

State:

```text
Event = stored
AI = retry pending
```

---

# 70. Notification Failure Does Not Mean Event Failure

If:

```text
Notification failed
```

the event remains:

```text
PROCESSED
```

with notification status:

```text
FAILED
```

unless the application explicitly defines notification as part of processing completion.

---

# 71. Real-Time Latency Budget

The system should measure:

```text
Gmail change
        ↓
Pub/Sub receipt
        ↓
History retrieval
        ↓
Message retrieval
        ↓
Event persistence
        ↓
AI start
        ↓
AI completion
        ↓
Notification
```

Each stage should have timestamps.

---

# 72. Latency Metrics

Track:

```text
source_to_pubsub_latency
pubsub_to_history_latency
history_to_message_latency
message_to_persistence_latency
AI_latency
notification_latency
end_to_end_latency
```

This allows future optimization.

---

# 73. "Real-Time" UI

The UI should display:

```text
Monitoring: LIVE
Last event: 14:03:21
Last Gmail sync: 14:03:21
```

when appropriate.

---

# 74. Monitoring Health Indicator

Suggested states:

```text
● LIVE
● RECONNECTING
● PAUSED
● ERROR
● AUTH REQUIRED
```

The exact visual style is defined by `07_UI_UX_Design.md`.

---

# 75. Desktop Popup Trigger

The popup should normally occur after:

```text
Event
+
Required AI analysis
+
Priority/notification decision
```

unless the user enables an immediate pre-AI notification mode.

---

# 76. Popup Content

Recommended:

```text
TOPIC
PRIORITY

Headline

AI Summary

Why it matters / key signal

Time

[Open Event]
[Open Source]
```

---

# 77. Popup Timing

The popup must not block:

```text
Gmail processing
AI processing
Database
```

It is a presentation event.

---

# 78. Popup Storm Protection

If multiple alerts arrive rapidly:

```text
100 emails
```

must not create:

```text
100 simultaneous popup windows
```

Use:

```text
Notification Queue
+
Priority
+
Deduplication
+
Rate limiting
+
Stacking/coalescing
```

---

# 79. Notification Priority

Suggested:

```text
CRITICAL
    immediate

HIGH
    immediate

MEDIUM
    queued/coalesced

LOW
    notification center only
```

The exact policy is user-configurable.

---

# 80. Attachment Handling

Attachment download is optional.

The monitoring event should not fail simply because:

```text
attachment download disabled
```

---

# 81. Attachment Download Modes

Possible:

```text
DISABLED
MANUAL
AUTO
AUTO_FOR_SELECTED_TYPES
```

---

# 82. Attachment Flow

```text
Relevant Gmail message
      |
      v
Attachment metadata
      |
      +--> Download disabled -> stop
      |
      +--> Download enabled
                |
                v
          Secure download
                |
                v
          Attachment storage
                |
                v
          Optional processing
```

---

# 83. Attachment Size Limit

A configurable maximum should prevent unexpectedly large downloads.

---

# 84. Attachment Security

Downloaded content must be treated as untrusted.

Never automatically execute attachments.

ZIP files must be protected against:

```text
Zip bombs
Path traversal
Unexpected extraction
```

---

# 85. Gmail Label-Based Filtering vs Search Query

The MVP should prefer:

```text
Gmail label ID
```

as the primary user-configured monitoring boundary.

Additional search/filter rules may be added later.

---

# 86. Multiple Labels Per Topic

Future configuration may support:

```text
Topic = Iran-US

Labels:
    Google Alerts/Iran
    Google Alerts/US-Iran
    Google Alerts/War
```

The contract should allow one topic to have multiple source mappings.

MVP may begin with one label per topic if simpler.

---

# 87. One Label to Multiple Topics

Avoid ambiguous mapping.

If the same label maps to multiple topics, define deterministic rules.

Preferred initial rule:

```text
One monitored Gmail label -> one topic
```

unless the user explicitly configures multi-topic matching.

---

# 88. Disabled Topic

If a topic is disabled:

```text
Continue Gmail monitoring for other topics.
```

Do not stop the global Gmail watch.

---

# 89. Paused Topic

A paused topic should normally:

```text
Stop creating new intelligence events for that topic
```

while preserving existing history.

The exact pause semantics should be configurable/documented.

---

# 90. Gmail Account Disconnect

When disconnected:

```text
Stop monitoring
Invalidate active monitoring state
Retain historical local data
Remove/disable provider credentials as appropriate
```

---

# 91. Reconnect

Reconnect should:

```text
Authenticate
Validate account
Reload labels
Rebuild topic mappings
Start/renew watch
Synchronize state
Resume monitoring
```

---

# 92. Startup Recovery

At application startup:

```text
Load monitor state
Check watch expiration
Check authentication
Check label configuration
Determine if history can be resumed
Resume or resync
```

---

# 93. Application Restart

A normal restart must not create duplicate events.

Use:

```text
External message ID
+
Database uniqueness
+
Idempotent processing
```

---

# 94. System Sleep / Hibernate

Windows may suspend the application.

On resume:

```text
Validate Gmail connection
Validate Pub/Sub subscriber
Validate watch expiration
Resume/reconnect
Check synchronization state
```

---

# 95. Network Change

When network changes:

```text
Subscriber may disconnect
Gmail requests may fail
```

The application should detect failures and reconnect.

---

# 96. Internet Outage

During an outage:

```text
Local history remains available
Monitoring state = RECONNECTING
```

After connectivity returns:

```text
Reconnect
Resume/resync
Process missed changes
```

---

# 97. Database Failure

If local database becomes unavailable:

```text
Do not ACK work that cannot be safely persisted.
```

The application should expose:

```text
DATABASE_ERROR
```

and attempt controlled recovery.

---

# 98. AI Backlog

If many alerts arrive:

```text
Gmail event intake
```

must not be blocked indefinitely by:

```text
AI processing
```

Use a bounded AI work queue.

---

# 99. AI Concurrency

AI concurrency should be configurable.

Example:

```text
max_ai_workers = 2
```

The actual value should be determined through testing/cost considerations.

---

# 100. Priority Before AI

If immediate classification is required, deterministic metadata may provide an initial priority:

```text
Topic
Source
User rule
```

AI-enhanced priority can follow.

The application must distinguish:

```text
initial priority
final priority
```

if both are supported.

---

# 101. Event Processing States

Recommended:

```text
RECEIVED
NORMALIZING
PERSISTED
AI_PENDING
AI_PROCESSING
AI_COMPLETED
PRIORITIZED
NOTIFICATION_PENDING
COMPLETED
RETRY_PENDING
FAILED
DUPLICATE
IGNORED
```

The final state model should be aligned with `05_System_Design.md`.

---

# 102. State Transition Example

```text
RECEIVED
   ↓
NORMALIZING
   ↓
PERSISTED
   ↓
AI_PENDING
   ↓
AI_PROCESSING
   ↓
AI_COMPLETED
   ↓
PRIORITIZED
   ↓
NOTIFICATION_PENDING
   ↓
COMPLETED
```

---

# 103. Failure Transition

Example:

```text
AI_PROCESSING
      |
      v
AI failure
      |
      v
RETRY_PENDING
      |
      v
AI_PROCESSING
```

After retry exhaustion:

```text
AI_FAILED
```

---

# 104. Duplicate Transition

```text
Message received
      |
      v
Existing event found
      |
      v
DUPLICATE
```

The system may still update synchronization progress.

---

# 105. Ignored Event

A message may be ignored if:

```text
Label not monitored
Topic disabled
Source rule excludes it
Message deleted
Unsupported event type
```

The reason should be observable in logs/diagnostics where useful.

---

# 106. Gmail History Ordering

The application must not assume every change arrives in perfect order across asynchronous delivery.

It should rely on Gmail history semantics and persisted state rather than Pub/Sub message ordering assumptions.

---

# 107. Pub/Sub Ordering

Do not depend on Pub/Sub ordering unless explicitly configured and justified.

The application must remain correct under duplicate/out-of-order notifications.

---

# 108. History Coalescing

Multiple Pub/Sub notifications may refer to mailbox changes that can be processed together.

The application may coalesce notifications to reduce API calls, provided that doing so does not compromise correctness or latency.

---

# 109. Batch Message Retrieval

Where Gmail API behavior and implementation allow, message retrieval should use efficient batching.

Do not make unnecessary sequential network calls for every message if batching materially improves performance.

---

# 110. Gmail API Quota

The implementation must minimize unnecessary calls.

Examples:

```text
Cache label metadata
Batch message retrieval
Avoid repeated full mailbox scans
Use history instead of polling
```

---

# 111. Label Cache

Label metadata can be cached locally.

The cache must be refreshed when:

```text
User requests refresh
Configuration changes
Periodic maintenance requires it
Gmail reports relevant changes
```

---

# 112. Source URL

Where possible, retain a source reference allowing the user to open the original Gmail message.

Do not rely solely on generated external URLs if the provider requires authenticated navigation.

---

# 113. Gmail Message Security

Email content is untrusted.

The application must defend against:

```text
Prompt injection
Malicious HTML
Tracking URLs
Unexpected MIME content
Oversized payloads
```

---

# 114. AI Prompt Injection Defense

The AI request should clearly separate:

```text
System/application instructions
Topic configuration
Source content
```

Source email text must be treated as untrusted data.

---

# 115. Data Minimization

Only send the required source content to AI.

Do not automatically send:

```text
Entire mailbox
Unrelated email history
Unrelated attachments
```

---

# 116. Sensitive Content

If user privacy settings restrict AI transmission, the application must respect them.

Potential future configuration:

```text
Allow AI processing
Only process selected labels
Exclude sensitive senders
Exclude attachments
```

---

# 117. AI Retry and Gmail State

If AI processing fails:

```text
Do not re-fetch Gmail unnecessarily.
```

The normalized event should already contain the required source information/reference.

---

# 118. Source Snapshot

For reproducibility, the application should retain a suitable normalized source snapshot or content reference according to privacy/retention settings.

This allows AI reprocessing without necessarily making another Gmail API call.

---

# 119. Raw Email Storage

The application should avoid storing more raw email content than necessary.

Storage/retention must follow the product's privacy policy.

---

# 120. Retention

Potential retention categories:

```text
Event metadata
AI analysis
Raw source content
Attachments
Logs
Audit records
```

Each may have separate retention settings.

---

# 121. Monitoring Diagnostics

The diagnostics screen should show:

```text
Gmail account
Gmail connection
Watch status
Watch expiration
Pub/Sub subscriber status
Last notification
Last history ID
Last successful sync
Last processing error
```

Never display secrets.

---

# 122. Manual Test

The application should provide a safe diagnostic capability to test:

```text
Gmail authentication
Label access
History retrieval
Pub/Sub connection
AI provider
Windows notification
```

without requiring a real trading alert.

---

# 123. Test Label

For development, use a dedicated label such as:

```text
InsightFlow/Test
```

rather than using real high-priority alerts.

The exact label is configurable.

---

# 124. Synthetic Event Test

A development test can simulate:

```text
GmailChangeNotification
```

without requiring Google Cloud.

This enables deterministic unit testing.

---

# 125. Integration Test

A controlled integration test may verify:

```text
Gmail
 -> Watch
 -> Pub/Sub
 -> Subscriber
 -> History
 -> Message
 -> Event
```

using a dedicated test account/project.

---

# 126. Failure Test Matrix

The implementation must test at least:

```text
Duplicate Pub/Sub message
Network outage
Expired OAuth
Expired watch
History ID unavailable
Gmail API timeout
Pub/Sub reconnect
Database unavailable
AI timeout
AI invalid response
Notification failure
Duplicate Gmail message
Missing monitored label
Disabled topic
```

---

# 127. Recovery Test Matrix

Test:

```text
Application restart
Windows sleep/resume
Internet disconnect/reconnect
Pub/Sub disconnect/reconnect
Watch expiration
Gmail token refresh
AI provider recovery
Database recovery
```

---

# 128. Real-Time Acceptance Criteria

The implementation is acceptable when:

```text
[ ] New monitored Gmail activity triggers Pub/Sub notification.
[ ] No 30/60-second polling loop is required for normal monitoring.
[ ] Relevant message is retrieved using Gmail history/message APIs.
[ ] Configured label determines topic association.
[ ] Duplicate delivery does not create duplicate events.
[ ] Event survives AI failure.
[ ] AI analysis is asynchronous/non-blocking to monitoring.
[ ] Notification is generated according to policy.
[ ] Application reconnects after temporary failures.
[ ] Watch renewal is automatic.
[ ] History recovery is implemented.
[ ] Application restart does not lose events.
[ ] UI shows real monitoring status.
```

---

# 129. Performance Acceptance Criteria

Measure and optimize:

```text
Notification arrival latency
History retrieval latency
Message retrieval latency
Event persistence latency
AI latency
Notification display latency
```

The exact target values should be established after real-world testing.

---

# 130. No Fake Real-Time

The UI must not display:

```text
LIVE
```

if:

```text
Gmail watch is expired
Subscriber is disconnected
Authentication is invalid
```

The displayed state must reflect actual monitoring health.

---

# 131. Real-Time Status Semantics

Recommended:

```text
LIVE
```

means:

```text
Gmail authorized
+
Watch active
+
Subscriber connected
+
No known synchronization error
```

---

# 132. Monitoring Pause

When the user presses:

```text
Pause Monitoring
```

the application should stop processing new monitoring events according to the configured pause behavior.

Historical data remains available.

---

# 133. Resume

When resumed:

```text
Validate connection
Check watch
Synchronize missed changes
Resume processing
```

---

# 134. Multiple Label Watch Strategy

Gmail watch operates at mailbox level/change notification scope rather than requiring one independent watch per user topic.

Therefore:

```text
One Gmail watch
      |
      v
Mailbox changes
      |
      v
Filter monitored labels
```

is preferred over attempting to create a separate watch for every topic.

---

# 135. Important Architecture Decision

Do NOT implement:

```text
Topic A -> Gmail polling
Topic B -> Gmail polling
Topic C -> Gmail polling
```

Instead:

```text
One Gmail monitoring pipeline
        |
        v
Label-based routing
        |
        +--> Topic A
        +--> Topic B
        +--> Topic C
```

---

# 136. Monitoring Manager

Recommended component:

```text
GmailMonitoringService
```

Responsibilities:

```text
Start
Stop
Reconnect
Renew watch
Track state
Receive change notification
Initiate synchronization
```

It should delegate:

```text
GmailClient
HistoryProcessor
Subscriber
StateRepository
```

rather than becoming a god class.

---

# 137. Suggested Infrastructure Classes

Potential structure:

```text
infrastructure/gmail/
├── gmail_client.py
├── gmail_authenticator.py
├── gmail_label_service.py
├── gmail_message_service.py
├── gmail_history_service.py
├── gmail_watch_service.py
├── gmail_mapper.py
├── gmail_models.py
└── exceptions.py

infrastructure/pubsub/
├── pubsub_subscriber.py
├── pubsub_message_parser.py
├── pubsub_ack_manager.py
└── exceptions.py

application/services/
├── gmail_monitoring_service.py
├── gmail_change_processor.py
└── process_intelligence_event.py
```

Names may be refined during implementation.

---

# 138. Suggested Interfaces

```text
GmailClient
GmailAuthenticator
GmailLabelService
GmailHistoryService
GmailWatchService
PubSubSubscriber
GmailChangeProcessor
MonitoringStateRepository
```

Only expose interfaces where there is a meaningful boundary or testing/provider variation.

---

# 139. Gmail Client Boundary

The application should not call:

```text
googleapiclient.discovery.build(...)
```

directly.

Only Gmail infrastructure should know the SDK.

---

# 140. Pub/Sub Client Boundary

The application should not directly import Google Pub/Sub SDK types.

The adapter converts them into internal models.

---

# 141. Google SDK Upgrade

A future Google SDK upgrade should ideally affect:

```text
infrastructure/gmail
infrastructure/pubsub
```

without forcing changes to:

```text
domain
application
presentation
```

---

# 142. Configuration Example

Conceptually:

```text
Gmail:
    enabled
    account
    client configuration reference

PubSub:
    enabled
    project
    topic
    subscription

Monitoring:
    reconnect policy
    history recovery policy
    concurrency

AI:
    provider
    profile defaults

Notifications:
    enabled
```

Secrets must remain outside ordinary configuration.

---

# 143. Google Cloud Project Separation

Recommended environments:

```text
Development
Testing
Production
```

should use appropriately separated Google Cloud resources where practical.

Do not use production Pub/Sub resources for development testing.

---

# 144. Local Development Mode

The application should support a mode where:

```text
Real Gmail = optional
Real Pub/Sub = optional
```

and synthetic events can drive the processing pipeline.

This is critical for development and AI-agent testing.

---

# 145. AI-Agent Development Requirement

Cursor/Codex/other agents should be able to test:

```text
GmailChangeNotification
```

using a fake source without needing real Google credentials.

---

# 146. Fake Gmail Provider

Test implementation:

```text
FakeGmailProvider
```

should support:

```text
Inject message
Inject history
Inject duplicate notification
Inject missing history
Inject timeout/error
```

---

# 147. Fake Pub/Sub Subscriber

Test implementation:

```text
FakePubSubSubscriber
```

should allow:

```text
Publish synthetic notification
Simulate duplicate
Simulate delay
Simulate disconnect
```

---

# 148. Contract Test

Every Gmail implementation should satisfy the source-provider contract.

Every notification implementation should satisfy the notification-provider contract.

Every AI provider should satisfy the AI-provider contract.

---

# 149. Security Acceptance Criteria

```text
[ ] OAuth secrets are not logged.
[ ] Tokens are stored securely.
[ ] HTML is sanitized.
[ ] Attachments are treated as untrusted.
[ ] ZIP traversal is blocked.
[ ] AI source content is treated as untrusted instructions.
[ ] Provider TLS verification is not disabled.
[ ] Credentials are not committed.
```

---

# 150. Operational Acceptance Criteria

```text
[ ] Watch expiration is visible.
[ ] Reconnect attempts are visible in diagnostics.
[ ] Last successful synchronization is visible.
[ ] Errors are correlated.
[ ] Duplicate handling is observable.
[ ] Resync state is visible.
```

---

# 151. End-to-End Example — Trump Alert

Example scenario:

```text
1. Google Alert generates an email.
2. Gmail receives the email.
3. Gmail applies:
      Google Alerts/Trump
4. Gmail records mailbox history.
5. Gmail watch notification reaches Pub/Sub.
6. InsightFlow receives Pub/Sub message.
7. Application extracts history ID.
8. Application retrieves changed history.
9. Application finds new message.
10. Application retrieves message.
11. Label ID maps to Topic = Trump.
12. Event is deduplicated.
13. IntelligenceEvent is persisted.
14. AI job is queued.
15. AI profile = Trading/Geopolitics.
16. AI generates summary.
17. Output is validated.
18. Priority engine evaluates impact.
19. Notification policy decides whether to notify.
20. Windows popup appears bottom-right.
21. User sees:
       Trump
       HIGH
       Short AI summary
22. User can open the event/source.
```

---

# 152. End-to-End Example — Celebrity

Exactly the same architecture:

```text
Google Alert
    |
    v
Gmail Label:
Google Alerts/Celebrity X
    |
    v
Gmail Watch
    |
    v
Pub/Sub
    |
    v
Topic = Celebrity X
    |
    v
AI Profile = Entertainment
```

No code change.

Only configuration changes.

---

# 153. End-to-End Example — Iran-US

```text
Gmail Label:
Google Alerts/Iran-US
```

maps to:

```text
Topic:
Iran-US Conflict
```

with:

```text
AI Profile:
Trading / Geopolitics
```

The AI output may emphasize:

```text
Oil
Gold
US equities
Indian equities
Risk sentiment
Possible market catalysts
```

depending on the configured profile.

---

# 154. Future Extension — Other Sources

The same processing pipeline can eventually accept:

```text
RSS
News API
Webhooks
Other email accounts
Other alert services
```

through:

```text
SourceProvider
```

without changing the core intelligence processing.

---

# 155. Final Architecture

```text
                    +------------------+
                    |      Gmail       |
                    +--------+---------+
                             |
                         Gmail Watch
                             |
                             v
                    +------------------+
                    |   Google Pub/Sub |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    | Pub/Sub Adapter  |
                    +--------+---------+
                             |
                             v
                  GmailChangeNotification
                             |
                             v
                  +---------------------+
                  | Gmail History       |
                  | Processor           |
                  +----------+----------+
                             |
                             v
                     Message IDs
                             |
                             v
                  +---------------------+
                  | Gmail Message       |
                  | Adapter             |
                  +----------+----------+
                             |
                             v
                  NormalizedSourceEvent
                             |
                             v
                  +---------------------+
                  | Topic Resolver       |
                  +----------+----------+
                             |
                             v
                    IntelligenceEvent
                             |
             +---------------+----------------+
             |               |                |
             v               v                v
        Persistence       AI Queue       Audit/Logs
                             |
                             v
                       AI Provider
                             |
                             v
                       AI Validator
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
                   Windows Popup / Center
```

---

# 156. Final Design Principles

The Gmail real-time subsystem must follow these rules:

```text
1. Push/event-driven first.
2. No 30/60-second polling for normal monitoring.
3. One Gmail watch can support the monitored mailbox.
4. Labels are configuration, not hardcoded business logic.
5. Pub/Sub notifications are change signals, not full messages.
6. Gmail history determines what changed.
7. Message IDs are used to retrieve actual messages.
8. Duplicate delivery must be safe.
9. History progress must be persisted carefully.
10. Prefer duplicate work over lost work.
11. AI processing must not block Gmail intake.
12. AI failure must not lose the event.
13. Notification failure must not lose the event.
14. Watch renewal must be automatic.
15. Reconnection must be automatic for temporary failures.
16. Authentication failures require user action.
17. History gaps require explicit resynchronization.
18. The UI must show the real monitoring state.
19. Provider SDKs remain behind adapters.
20. The entire design must remain generic for any monitored topic.
```

---

# 157. Implementation Readiness Checklist

Before implementing the Gmail subsystem:

```text
[ ] Google Cloud project created.
[ ] Gmail API enabled.
[ ] Pub/Sub API enabled.
[ ] OAuth consent configuration completed.
[ ] OAuth scopes reviewed.
[ ] Pub/Sub topic created.
[ ] Pub/Sub subscription created.
[ ] Gmail watch permissions/configuration validated.
[ ] Local secure credential storage selected.
[ ] Gmail label discovery tested.
[ ] Gmail history API behavior tested.
[ ] Watch expiration behavior tested.
[ ] Duplicate notifications tested.
[ ] History gap behavior tested.
[ ] Reconnect behavior tested.
[ ] Application restart recovery tested.
[ ] Fake Gmail provider implemented.
[ ] Fake Pub/Sub provider implemented.
[ ] Integration tests created.
```

---

# 158. Final Acceptance Statement

The Gmail monitoring implementation is considered successful when a user can:

```text
1. Connect a Gmail account.
2. Select a Gmail label.
3. Associate that label with any user-defined topic.
4. Start monitoring.
5. Receive Gmail changes through the event-driven pipeline.
6. Have the relevant message retrieved automatically.
7. Have the event processed by AI.
8. Receive a concise AI summary.
9. Receive a Windows bottom-right notification according to policy.
10. Open the original source.
11. Optionally download/process attachments.
12. Continue monitoring after temporary network/API failures.
13. Restart the application without losing or duplicating events.
14. Add a completely different topic without changing source code.
```

The key architectural outcome is:

> **InsightFlow AI monitors Gmail as an event source, not as a mailbox that must be repeatedly polled. Gmail labels determine what the user cares about, while the generic intelligence pipeline determines what happens next.**
