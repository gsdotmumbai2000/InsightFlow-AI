# InsightFlow AI — UI/UX Design

**Document:** `07_UI_UX_Design.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `05_System_Design.md`, `06_Database_Design.md`

---

# 1. Purpose

This document defines the user interface and user experience for InsightFlow AI.

The objective is to make the application feel like a **real-time personal intelligence monitor**, not like an email client.

The user should be able to:

1. Configure topics.
2. Connect Gmail.
3. Monitor labeled information in real time.
4. Receive AI summaries immediately.
5. Understand why an item matters.
6. Open the original source when required.
7. Search historical intelligence.
8. Review topic timelines.
9. Manage AI profiles.
10. Optionally download/process attachments.
11. Eventually create and review YouTube content.

The application must remain generic.

It must never be designed specifically around:

```text
Trump
Iran
Modi
NIFTY
Celebrities
```

Those are examples of topics.

---

# 2. UX Philosophy

The application should follow this principle:

> **The user should see the important information first, understand its significance quickly, and only then have the option to investigate deeper.**

The preferred information hierarchy is:

```text
What happened?
      ↓
Why does it matter?
      ↓
How important is it?
      ↓
What may happen next?
      ↓
Show me the source.
```

---

# 3. Primary User Workflow

The main workflow is:

```text
Configure Topic
      |
      v
Connect Gmail
      |
      v
Enable Monitoring
      |
      v
Wait for Information
      |
      v
Real-Time Event
      |
      v
AI Analysis
      |
      v
Desktop Popup
      |
      v
User Reads Summary
      |
      +---- Ignore
      |
      +---- Open Details
      |
      +---- Open Source
      |
      +---- Save/Track
      |
      +---- Future: Create Content
```

---

# 4. Design Principles

## 4.1 Real-Time First

The dashboard should communicate live activity.

Avoid making the user manually refresh the application.

---

## 4.2 Summary First

The first visible information should be the AI summary, not raw email HTML.

---

## 4.3 Source Remains Available

AI output must never hide the original source.

The user should be able to open:

```text
Original Email
Original Gmail Thread
Original Source URL
```

where available.

---

## 4.4 Topic Agnostic

The UI must not contain hardcoded topic categories.

The user creates:

```text
Trump
Iran
Modi
Celebrity X
Company Y
Technology Z
```

as ordinary topics.

---

## 4.5 Progressive Disclosure

Simple information appears first.

Advanced information appears when requested.

Example:

```text
Popup
  ↓
Summary
  ↓
Details
  ↓
AI Analysis
  ↓
Source
  ↓
Raw Email
```

---

# 5. Main Application Window

The main window is the central control center.

Recommended layout:

```text
+--------------------------------------------------------------------+
| InsightFlow AI                         ● Connected       ⚙ Settings |
+--------------------------------------------------------------------+
|                                                                    |
|  SIDEBAR             LIVE INTELLIGENCE                            |
|                                                                    |
|  Dashboard            +------------------------------------------+ |
|  Topics               | HIGH   Trump update                      | |
|  Intelligence         |        Important geopolitical update     | |
|  Stories              |        10:42 AM                          | |
|  Notifications        +------------------------------------------+ |
|  Attachments          | MED    Iran development                   | |
|  AI Profiles          |        AI summary...                      | |
|  Rules                +------------------------------------------+ |
|  Content              | LOW    Celebrity update                  | |
|                       |        AI summary...                      | |
|                       +------------------------------------------+ |
|                                                                    |
+--------------------------------------------------------------------+
| Gmail ● | AI ● | Database ● | Notifications ● | Monitoring ●      |
+--------------------------------------------------------------------+
```

---

# 6. Main Navigation

The sidebar should contain:

```text
Dashboard
Intelligence
Topics
Stories
Notifications
Attachments
AI Profiles
Rules
Content
Settings
```

Future items may be added without changing the basic navigation architecture.

---

# 7. Dashboard

The dashboard is the default screen.

It should answer:

```text
What is happening right now?
Is monitoring working?
What important things happened recently?
```

---

# 8. Dashboard Sections

Recommended sections:

```text
System Status
Live Feed
Important Events
Topic Activity
Recent Stories
Processing Status
```

---

# 9. System Status Widget

Example:

```text
SYSTEM STATUS

Gmail          ● Connected
Real-Time      ● Active
AI             ● Connected
Database       ● Healthy
Notifications  ● Ready
```

Clicking a status should open relevant diagnostics.

---

# 10. Monitoring Status

The dashboard should show:

```text
Monitoring: ACTIVE
```

or:

```text
Monitoring: PAUSED
```

or:

```text
Monitoring: RECONNECTING
```

The user must not need to inspect logs to know whether monitoring is operational.

---

# 11. Live Intelligence Feed

The live feed is the most important dashboard component.

Each item should show:

```text
Priority
Topic
Headline
AI Summary
Time
Source
```

Example:

```text
┌──────────────────────────────────────────────────────────────┐
│ HIGH  TRUMP                                      10:42 AM    │
│                                                             │
│ New statement raises uncertainty around Iran policy         │
│                                                             │
│ Trump indicated that further decisions may depend on...     │
│                                                             │
│ Potential impact: US markets / crude / geopolitical risk    │
│                                                             │
│ [Details] [Open Source]                                     │
└──────────────────────────────────────────────────────────────┘
```

---

# 12. Intelligence Table

A table view should also be available.

Recommended columns:

| Column | Purpose |
|---|---|
| Priority | Importance |
| Time | Event time |
| Topic | Monitored topic |
| Headline | AI/source headline |
| Summary | Short AI summary |
| Impact | Key impact |
| Source | Source |
| Status | Processing state |

---

# 13. Intelligence Table Example

```text
+------+----------+----------+----------------------+----------------+
| Pri  | Time     | Topic    | Headline             | Status         |
+------+----------+----------+----------------------+----------------+
| HIGH | 10:42 AM | TRUMP    | New statement...     | Completed      |
| HIGH | 10:38 AM | IRAN     | Iran response...     | Completed      |
| MED  | 10:30 AM | MODI     | New announcement...  | Completed      |
| LOW  | 10:15 AM | CELEB X  | New interview...     | Completed      |
+------+----------+----------+----------------------+----------------+
```

---

# 14. Table Interaction

Rows should support:

```text
Single click
    -> Select

Double click
    -> Open details

Right click
    -> Context menu
```

Context menu:

```text
Open Details
Open Original Source
Mark Important
Ignore
Reprocess with AI
Add to Story
Create Content
Copy Summary
```

Future actions can be added.

---

# 15. Priority Indicators

Use clear visual indicators:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

The exact colors should follow the application's theme system rather than being hardcoded into business logic.

Recommended visual hierarchy:

```text
CRITICAL -> strongest visual emphasis
HIGH     -> strong emphasis
MEDIUM   -> moderate emphasis
LOW      -> subtle
```

Do not rely on color alone.

Display the text label too.

---

# 16. Event Details Window

Clicking an intelligence item opens the details view.

Recommended layout:

```text
+----------------------------------------------------------------+
| Trump — New statement raises uncertainty             [X]      |
+----------------------------------------------------------------+
| HIGH | TRUMP | 10:42 AM | Google Alerts                       |
+----------------------------------------------------------------+
|                                                                |
| AI SUMMARY                                                     |
| Trump indicated that...                                        |
|                                                                |
+----------------------------------------------------------------+
| WHY IT MATTERS                                                 |
| Potential implications for geopolitical risk and markets.      |
|                                                                |
+----------------------------------------------------------------+
| WHAT TO WATCH                                                  |
| Further policy statements and market reaction.                |
|                                                                |
+----------------------------------------------------------------+
| SOURCE FACTS                                                   |
| • ...                                                          |
| • ...                                                          |
+----------------------------------------------------------------+
| AI CONFIDENCE: 82%                                             |
+----------------------------------------------------------------+
| [Open Gmail] [Original Source] [Reprocess AI] [Close]          |
+----------------------------------------------------------------+
```

---

# 17. Event Details Sections

The details page should support:

```text
Summary
Why It Matters
Source Facts
AI Interpretation
What To Watch
Entities
Market Impact
Attachments
Original Source
Processing Information
```

Sections may be collapsed/expanded.

---

# 18. Source Facts vs AI Interpretation

The UI must clearly distinguish:

### Source Facts

Information directly supported by the source.

### AI Interpretation

AI-generated analysis.

Example:

```text
SOURCE FACT
The email reports that a new statement was issued.

AI INTERPRETATION
This may increase short-term geopolitical uncertainty.
```

This distinction is especially important for trading-related analysis.

---

# 19. Market Impact Section

Only display when the selected AI profile produces market analysis.

Example:

```text
MARKET IMPACT

Potential direction:
Uncertain

Potentially affected:
• Crude oil
• US equities
• Indian equities
• Safe-haven assets

Reason:
Potential escalation could increase risk aversion.
```

The UI must never present AI predictions as guaranteed market outcomes.

---

# 20. What To Watch

A dedicated section should show future developments worth monitoring.

Example:

```text
WHAT TO WATCH

1. Official response
2. Policy announcement
3. Oil price reaction
4. US futures movement
```

This is particularly useful for the user's trading workflow.

---

# 21. AI Confidence

If the AI provider/profile supplies confidence, display it.

Example:

```text
AI CONFIDENCE
82%
```

Add a tooltip:

```text
AI confidence is an estimate produced by the analysis workflow.
It is not a probability of the event occurring.
```

---

# 22. Original Source

The event detail view should provide:

```text
[Open Gmail]
[Open Original URL]
```

where available.

Opening the source should use the user's default browser/application.

---

# 23. Raw Email View

An optional raw view should show:

```text
From
To
Date
Subject
Labels
Original content
Attachments
```

HTML email should be sanitized before rendering.

---

# 24. Topic Management

The Topics screen is central to the application's generic design.

Example:

```text
+-------------------------------------------------------------+
| Topics                                      [+ New Topic]    |
+-------------------------------------------------------------+
| Status | Topic       | Source | AI Profile       | Alerts  |
+-------------------------------------------------------------+
| ●      | TRUMP       | Gmail  | Trading/Geo      | ON      |
| ●      | IRAN        | Gmail  | Trading/Geo      | ON      |
| ●      | MODI        | Gmail  | Politics         | ON      |
| ●      | CELEB X     | Gmail  | Entertainment    | ON      |
+-------------------------------------------------------------+
```

---

# 25. Topic Creation

New Topic form:

```text
Topic Name
Description
Source
Source Identifier / Gmail Label
AI Profile
Notification Policy
Priority Policy
Attachment Policy
Enabled
```

Buttons:

```text
[Save]
[Cancel]
```

---

# 26. Topic Creation Principle

A user should be able to add a new topic without:

```text
Writing code
Changing Python files
Changing database schema
Changing AI source code
```

---

# 27. Gmail Label Selection

For Gmail topics, the UI should ideally allow:

```text
[Select Gmail Label ▼]
```

instead of requiring the user to manually type a label.

Example:

```text
Gmail Labels

☐ TRUMP
☐ IRAN
☐ MODI
☐ CELEBRITY_X
☐ GOOGLE_ALERTS
```

---

# 28. AI Profile Selection

Example:

```text
AI Profile

[ Trading / Geopolitics ▼ ]
```

Available profiles are user-configurable.

---

# 29. Notification Policy

Topic-level configuration:

```text
Notify:
[✓] Critical
[✓] High
[ ] Medium
[ ] Low

Quiet Hours:
22:00 - 06:00

Sound:
Enabled
```

---

# 30. Attachment Policy

Example:

```text
Attachment Handling

Download attachments:
[ ] Disabled
[✓] Enabled

Maximum file size:
20 MB

Allowed types:
PDF
Excel
CSV
ZIP

Process content:
[✓]
```

The default should be conservative.

---

# 31. Gmail Connection Screen

The Gmail setup screen should guide the user through:

```text
1. Connect Google Account
2. Authorize permissions
3. Verify connection
4. Select labels
5. Enable monitoring
```

---

# 32. Gmail Connection Status

Example:

```text
GMAIL

Account:
user@example.com

Status:
● Connected

Push Monitoring:
● Active

Last Event:
10:42:03 AM

Watch:
Valid

[Reconnect]
[Disconnect]
[Test Connection]
```

---

# 33. Real-Time Monitoring Indicator

The application should provide a prominent indicator:

```text
● LIVE
```

when event monitoring is active.

Possible states:

```text
● LIVE
◐ CONNECTING
○ PAUSED
! ERROR
```

The exact symbols may be represented using accessible text/status components.

---

# 34. Notifications Screen

This screen shows notification history.

Columns:

```text
Time
Priority
Topic
Headline
Status
```

Filters:

```text
Topic
Priority
Date
Status
```

---

# 35. Desktop Popup Design

The popup is a major product feature.

It should appear from the **bottom-right corner of the Windows desktop**.

Conceptual design:

```text
                                      +----------------------------+
                                      | HIGH  TRUMP       10:42 AM |
                                      |                            |
                                      | New statement raises       |
                                      | geopolitical uncertainty  |
                                      |                            |
                                      | AI: Further developments  |
                                      | may affect risk sentiment.|
                                      |                            |
                                      | [Details] [Open Source]   |
                                      +----------------------------+
```

---

# 36. Popup Animation

Preferred behavior:

```text
Hidden
  |
  v
Slide/Fade In
  |
  v
Visible
  |
  v
Fade Out
  |
  v
Hidden
```

The animation must be smooth and non-blocking.

---

# 37. Popup Duration

The duration should be configurable.

Example:

```text
5 seconds
10 seconds
15 seconds
Until dismissed
```

High-priority notifications may remain longer.

---

# 38. Popup Actions

Minimum actions:

```text
[Details]
[Open Source]
[X]
```

Future:

```text
[Mark Important]
[Ignore Topic]
[Create Content]
```

---

# 39. Popup Stacking

If multiple events arrive quickly:

```text
Notification 1
Notification 2
Notification 3
```

the application must avoid covering the entire desktop.

Preferred behavior:

```text
+------------------+
| Notification 3   |
+------------------+
| Notification 2   |
+------------------+
| Notification 1   |
+------------------+
```

or a controlled queue.

---

# 40. Notification Storm Protection

If dozens of messages arrive simultaneously, the UI should not create dozens of overlapping popups.

Possible behavior:

```text
3 important notifications
+
"7 more events available"
```

Clicking opens the notification center.

---

# 41. Notification Center

A notification center may display:

```text
Unread
Important
Recent
All
```

with filtering by topic.

---

# 42. System Tray

The application should support Windows system tray operation.

Tray menu:

```text
InsightFlow AI

● Monitoring Active

Open Dashboard
Pause Monitoring
Resume Monitoring
Topics
Notifications
Settings
View Logs
Exit
```

---

# 43. Minimize Behavior

Closing the main window should optionally:

```text
Minimize to tray
```

rather than terminate the monitoring process.

The user should be clearly informed of this behavior.

---

# 44. Application Exit

When exiting:

```text
Are you sure you want to stop real-time monitoring?
```

if monitoring is active.

Possible options:

```text
[Exit]
[Keep Running in Tray]
[Cancel]
```

---

# 45. Search Screen

Search should support:

```text
Keyword
Topic
Priority
Date range
Source
AI profile
```

Example:

```text
Search:
[ Iran sanctions                         ]

Topic:
[ All ▼ ]

Priority:
[ All ▼ ]

Date:
[ Last 30 days ▼ ]

[Search]
```

---

# 46. Search Results

Example:

```text
+--------------------------------------------------------------+
| 27 results                                                   |
+--------------------------------------------------------------+
| HIGH | IRAN | Aug 8 | New sanctions discussed               |
| MED  | IRAN | Aug 7 | Government response                  |
| HIGH | TRUMP| Aug 6 | Statement regarding sanctions        |
+--------------------------------------------------------------+
```

---

# 47. Stories Screen

Future story view:

```text
+-------------------------------------------------------------+
| STORIES                                                     |
+-------------------------------------------------------------+
| HIGH | Iran escalation                                     |
|      | 14 events | Last update: 10:42 AM                   |
|                                                             |
| HIGH | US tariff developments                             |
|      | 8 events | Last update: 09:35 AM                    |
+-------------------------------------------------------------+
```

---

# 48. Story Details

```text
STORY: Iran escalation

Current Summary
---------------

Timeline
---------

10:42 AM  New statement
09:15 AM  Government response
08:40 AM  Initial report

AI Analysis
-----------

What changed?
What remains uncertain?
What to watch?
```

---

# 49. Timeline Visualization

A story timeline should visually show:

```text
● 10:42  New development
|
● 09:15  Response
|
● 08:40  Initial report
|
● 07:20  Earlier signal
```

This will be especially valuable for fast-moving geopolitical topics.

---

# 50. AI Profiles Screen

Example:

```text
+--------------------------------------------------------------+
| AI Profiles                                  [+ New Profile] |
+--------------------------------------------------------------+
| Profile              | Version | Used By | Status            |
+--------------------------------------------------------------+
| Trading/Geopolitics  | v4      | 5 topics| Active            |
| Entertainment        | v2      | 2 topics| Active            |
| General News         | v1      | 3 topics| Active            |
+--------------------------------------------------------------+
```

---

# 51. AI Profile Editor

Sections:

```text
Profile Name
Description
System Instructions
Output Schema
Model Preferences
Version
```

Buttons:

```text
[Save New Version]
[Test Profile]
[Cancel]
```

---

# 52. Prompt Testing

The user should eventually be able to test a profile with sample text.

Example:

```text
Sample Input
------------

[paste sample news/email]

[Run AI Test]

Output
------

Summary:
...

Impact:
...

Confidence:
...
```

This makes AI behavior configurable without modifying code.

---

# 53. Rules Screen

Example:

```text
+-------------------------------------------------------------+
| Rules                                       [+ New Rule]     |
+-------------------------------------------------------------+
| Enabled | Rule                        | Priority | Status   |
+-------------------------------------------------------------+
| ✓       | High Trump -> notify         | 10       | Active   |
| ✓       | Iran -> create story         | 20       | Active   |
+-------------------------------------------------------------+
```

---

# 54. Rule Editor

Conceptual UI:

```text
WHEN

Topic              [TRUMP ▼]

Priority            [>= HIGH ▼]

AND / OR

Keyword             [Iran]

THEN

[Show Notification]
[Create Story]
[Create Content Job]
```

The first MVP may implement only a limited rule set.

---

# 55. Attachments Screen

Example:

```text
+----------------------------------------------------------------+
| Attachments                                                    |
+----------------------------------------------------------------+
| Date | Topic | Filename | Type | Size | Download | Processing |
+----------------------------------------------------------------+
| ...  | IRAN  | report.pdf| PDF | 2MB | Done | Complete       |
+----------------------------------------------------------------+
```

---

# 56. Attachment Detail

Display:

```text
Filename
Type
Size
Source Event
Download Status
Processing Status
Extracted Content
```

Actions:

```text
[Open File]
[Open Source]
[Reprocess]
[Delete]
```

---

# 57. Settings Screen

Settings should be grouped.

```text
General
Gmail
AI
Notifications
Attachments
Storage
Privacy
Logging
Advanced
```

Avoid a single enormous settings page.

---

# 58. General Settings

Possible options:

```text
Start with Windows
Minimize to tray
Theme
Language
Time format
Default date range
```

---

# 59. Notification Settings

```text
Enable desktop notifications
Duration
Sound
Minimum priority
Quiet hours
Maximum simultaneous popups
Notification grouping
```

---

# 60. AI Settings

```text
Default provider
Default model
Maximum concurrent requests
Daily request limit
Daily cost limit
Retry policy
```

---

# 61. Privacy Settings

```text
Email content retention
AI analysis retention
Attachment retention
Raw source retention
Clear history
Delete all local data
```

Destructive actions must require confirmation.

---

# 62. Storage Settings

Display:

```text
Database location
Database size
Attachment location
Attachment size
Log size
```

Actions:

```text
[Backup]
[Restore]
[Open Storage Folder]
[Cleanup]
```

---

# 63. Diagnostics Screen

Useful for troubleshooting:

```text
Gmail:
Connected

Pub/Sub:
Active

AI:
Connected

Database:
Healthy

Notifications:
Ready

Last event:
10:42:03

Last error:
None
```

Advanced users can view logs.

---

# 64. Error Presentation

Errors should be understandable.

Bad:

```text
google.auth.exceptions.RefreshError
```

Better:

```text
Gmail connection expired.

InsightFlow could not renew the Google connection.

[Reconnect]
[View Details]
```

Technical details may be expandable.

---

# 65. Empty States

Every major screen needs an empty state.

Example Topics:

```text
No topics configured.

Create a topic to begin monitoring information.

[+ Create Topic]
```

---

# 66. Loading States

Use meaningful states:

```text
Connecting to Gmail...
Loading labels...
Waiting for real-time events...
Generating AI summary...
Loading history...
```

Avoid generic endless spinners.

---

# 67. Offline States

If internet connectivity is lost:

```text
OFFLINE

Gmail monitoring is temporarily unavailable.

InsightFlow will reconnect automatically.
```

Local history should remain accessible.

---

# 68. Accessibility

UI components should provide:

- Keyboard navigation.
- Accessible labels.
- Tooltips.
- Text alternatives to color.
- Sufficient contrast.
- Visible focus.
- Logical tab order.

---

# 69. Keyboard Shortcuts

Potential shortcuts:

```text
Ctrl+K    Search
Ctrl+T    New Topic
Ctrl+,    Settings
Esc       Close popup/dialog
Enter     Open selected item
Ctrl+R    Refresh local view
```

Exact shortcuts can be finalized during implementation.

---

# 70. Responsive Desktop Layout

The application should support reasonable resizing.

Minimum recommended window size:

```text
1000 x 650
```

The exact minimum may be adjusted during UI implementation.

---

# 71. Window State Persistence

The application should remember:

```text
Window size
Window position
Sidebar width
Selected page
Column widths
Sort order
Filter state
```

These should be user settings, not hardcoded.

---

# 72. Theme

The UI should support at least:

```text
System
Light
Dark
```

The initial design should not hardcode colors throughout individual widgets.

Use a centralized theme/style system.

---

# 73. Typography

The interface should use a consistent typography hierarchy:

```text
Application title
Page title
Section title
Headline
Summary
Metadata
Secondary information
```

AI summaries should be easy to scan.

---

# 74. Information Density

The dashboard should favor information density without becoming cluttered.

Preferred:

```text
Headline
1–3 line summary
Priority
Topic
Time
```

Detailed analysis belongs in the event details view.

---

# 75. Table Column Customization

Users should eventually be able to:

```text
Show/hide columns
Resize columns
Reorder columns
Reset columns
```

---

# 76. Filtering

Common filters should be available without opening advanced dialogs.

Example:

```text
[All Topics ▼] [All Priorities ▼] [Today ▼]
```

---

# 77. Sorting

Intelligence table should support sorting by:

```text
Time
Priority
Topic
Status
```

Default:

```text
Newest first
```

---

# 78. Live Feed Behavior

When a new event arrives:

```text
New event
   |
   v
Insert at top
   |
   v
Subtle visual highlight
   |
   v
Notification if policy allows
```

Do not automatically move the user's scroll position if they are reading older events.

---

# 79. Scroll Preservation

If the user is reading older items and a new event arrives:

```text
Do not jump to top.
```

Instead show:

```text
↑ 3 new events
```

Clicking it moves to the latest items.

---

# 80. Event Read State

Events may have:

```text
Unread
Read
Important
Archived
```

This is separate from processing status.

---

# 81. Processing Status vs User Status

Do not confuse:

```text
Processing status
```

with:

```text
User read status
```

Example:

```text
Processing:
COMPLETED

User:
UNREAD
```

---

# 82. Notification vs Event

A single event may generate:

```text
0 notifications
1 notification
multiple notifications
```

The event remains the primary intelligence object.

---

# 83. Popup Click Flow

```text
Popup appears
      |
      v
User clicks Details
      |
      v
Main window activated
      |
      v
Event details opened
      |
      v
Notification marked OPENED
```

---

# 84. Source Click Flow

```text
Open Source
      |
      v
Resolve source URL
      |
      v
Default browser
```

For Gmail:

```text
Open Gmail message/thread
```

where possible.

---

# 85. Topic Pause Flow

User clicks:

```text
Pause
```

UI:

```text
Pause topic "TRUMP"?

Existing history will remain available.

[Pause] [Cancel]
```

Pausing must not delete historical information.

---

# 86. Topic Disable Flow

Disabling a topic means:

```text
Stop new processing
```

Historical records remain.

---

# 87. Reprocess Flow

User selects:

```text
Reprocess with AI
```

The UI should show:

```text
Select AI Profile
[Trading/Geopolitics ▼]

[Reprocess]
```

The existing analysis should remain until the new analysis succeeds.

---

# 88. AI Regeneration UX

If regeneration fails:

```text
Previous analysis remains available.

New analysis:
FAILED

[Retry]
```

Do not replace good historical data with an error.

---

# 89. Story Creation UX

Future:

```text
Select events
    |
    v
[Create Story]
    |
    v
Story title
Story summary
    |
    v
Save
```

AI-assisted story creation can be added later.

---

# 90. Content Generation UX

Future:

```text
Event/Story
    |
    v
[Create YouTube Short]
    |
    v
Target:
3 minutes

AI generates script
    |
    v
User Review
    |
    v
[Approve]
```

---

# 91. YouTube Safety UX

Publishing should clearly show:

```text
DRAFT
REVIEW REQUIRED
```

before publication.

Initial release must not silently publish generated videos.

---

# 92. AI Generated Content Label

Generated content should be visibly identified as:

```text
AI Generated Draft
```

until approved.

---

# 93. User Confirmation for Destructive Actions

Require confirmation for:

```text
Delete topic history
Delete attachments
Clear all history
Delete database
Restore backup
Disconnect account
```

---

# 94. Confirmation Dialog Design

Example:

```text
Delete 342 events?

This action cannot be undone.

[Cancel] [Delete]
```

The destructive action should be visually distinct.

---

# 95. Contextual Help

Use tooltips and small help links rather than overwhelming the user with documentation.

Example:

```text
AI Confidence
ⓘ
```

Tooltip:

```text
AI confidence is an estimated signal and is not a guarantee.
```

---

# 96. First-Run Experience

On first launch:

```text
Welcome to InsightFlow AI

Monitor information in real time and receive AI-powered intelligence.

Step 1: Connect Gmail
Step 2: Select a label
Step 3: Choose an AI profile
Step 4: Enable notifications

[Get Started]
```

---

# 97. First-Run Wizard

Recommended steps:

```text
1. Welcome
2. Gmail Authorization
3. Gmail Label Selection
4. AI Provider Setup
5. Notification Test
6. Finish
```

The user should be able to skip optional configuration.

---

# 98. Notification Test

During setup:

```text
[Send Test Notification]
```

The popup should appear in the real Windows bottom-right location.

This confirms notification functionality before real monitoring begins.

---

# 99. Gmail Label Test

After selecting a label:

```text
[Send Test Event]
```

The application should verify that it can retrieve and process a matching message.

---

# 100. AI Test

The user should be able to run a small test before enabling a topic.

Example:

```text
AI connection: ● OK
Model: Claude ...
Response validation: ● OK
```

---

# 101. Dashboard Default

After setup, the application opens on:

```text
Dashboard
```

with:

```text
Monitoring: ACTIVE
```

if the user enabled monitoring.

---

# 102. Status Bar

Bottom status bar:

```text
Gmail ● Connected
AI ● Ready
Database ● Healthy
Notifications ● Ready
Monitoring ● Active
```

Clicking a status opens diagnostics.

---

# 103. Notification Sound

Sound should be optional.

Possible configuration:

```text
Critical: Sound
High: Sound
Medium: Silent
Low: Silent
```

---

# 104. Quiet Hours

The application should support quiet hours.

Example:

```text
22:00 -> 06:00
```

During quiet hours:

```text
Process normally
Store normally
Do not interrupt user unless configured
```

This is important because monitoring should continue even when notifications are suppressed.

---

# 105. Critical Override

Future option:

```text
Allow Critical notifications during quiet hours
```

---

# 106. Topic Activity Visualization

Dashboard may show:

```text
TRUMP       ███████████  24
IRAN        ███████       14
MODI        ████           8
CELEB X     ██             4
```

The visualization is for activity, not importance unless explicitly labeled.

---

# 107. Recent Activity

Show:

```text
Events today
High-priority events
Unread events
AI failures
Pending processing
```

---

# 108. Processing Monitor

Advanced dashboard widget:

```text
PROCESSING

Received:       124
Completed:      120
AI Pending:       2
Retry Pending:    1
Failed:           1
```

---

# 109. AI Usage Widget

Future:

```text
AI USAGE

Requests today: 124
Estimated tokens: 82K
Estimated cost: $0.84
```

This is especially useful when monitoring many topics.

---

# 110. Notification Preferences Per Topic

Each topic should be able to override global notification settings.

Hierarchy:

```text
Global Settings
      |
      v
Topic Settings
      |
      v
Rule Override
```

More specific configuration wins.

---

# 111. Accessibility and Color

Never communicate priority only through color.

Use:

```text
HIGH
MEDIUM
LOW
```

plus icons/labels where appropriate.

---

# 112. Error Badges

Examples:

```text
Gmail       ! Error
AI          ! Error
Database    ● Healthy
```

Clicking opens details.

---

# 113. Network Reconnection UX

When reconnecting:

```text
Gmail
◐ Reconnecting...
```

Avoid repeated intrusive popups for transient failures.

A persistent status indicator is preferable.

---

# 114. AI Failure UX

If AI fails:

```text
EVENT RECEIVED

AI summary unavailable.

The original source has been preserved.

[Retry AI]
```

Do not hide the event.

---

# 115. Duplicate UX

Duplicates normally should not interrupt the user.

They may appear in processing diagnostics but should not generate repeated notifications.

---

# 116. Unsupported Attachment UX

Example:

```text
Attachment:
file.xyz

Status:
Unsupported file type

[Download]
```

The application should not pretend it processed unsupported content.

---

# 117. Large Attachment UX

Example:

```text
report.zip — 245 MB

This exceeds the configured maximum size of 20 MB.

[Download Anyway]
[Cancel]
```

Only allow override if the security policy permits it.

---

# 118. Navigation Breadcrumbs

For deep screens:

```text
Intelligence > TRUMP > Event Details
```

This helps users understand where they are.

---

# 119. Modal vs Non-Modal

Use modal dialogs for:

```text
Delete
Restore
OAuth setup
Critical configuration
```

Use non-modal pages/panels for:

```text
Event details
Search
History
AI analysis
```

---

# 120. UI State Persistence

Persist:

```text
Selected topic
Filters
Column widths
Sort
Window size
Theme
```

Do not persist temporary processing state in UI settings.

Processing state belongs in the application/database layer.

---

# 121. UI Architecture Boundary

The UI should communicate through:

```text
ViewModel / Controller
       |
       v
Application Use Case
```

not:

```text
Widget -> Repository
Widget -> Gmail API
Widget -> Bedrock
```

---

# 122. ViewModel Responsibilities

ViewModels may handle:

- UI state.
- Formatting.
- Loading state.
- Error presentation.
- User commands.

ViewModels must not implement domain business rules.

---

# 123. Table Model Responsibilities

Table models should:

- Transform result DTOs into rows.
- Handle sorting/filtering presentation.
- Notify UI of changes.

They should not execute SQL directly.

---

# 124. Notification Presentation Boundary

The popup component should receive:

```text
NotificationViewModel
```

rather than raw database records.

---

# 125. UI Performance

The UI must remain responsive while:

```text
AI is running
Gmail is retrieving data
Attachments are downloading
Search is running
Database maintenance is occurring
```

---

# 126. Large History Lists

Do not load thousands of events into the UI at once.

Use:

```text
Pagination
Lazy loading
Virtualized table where appropriate
```

---

# 127. Infinite Scroll

Optional future feature:

```text
Scroll near bottom
      |
      v
Load older events
```

The first version may use pagination.

---

# 128. Live Feed Performance

New events should be inserted incrementally rather than rebuilding the entire table.

---

# 129. UI Logging

The UI should show user-friendly messages.

Detailed logs remain in the diagnostic/logging system.

---

# 130. UX for AI Latency

During AI processing:

```text
AI ANALYSIS
◐ Processing...
```

The original event should already be visible if available.

This avoids making the user wait for AI before knowing that something arrived.

---

# 131. Progressive Event Display

Preferred sequence:

```text
Event received
   |
   v
Show "Processing..."
   |
   v
AI complete
   |
   v
Update summary
   |
   v
Notify if required
```

This makes the system feel genuinely real-time.

---

# 132. Event Arrival vs AI Completion

The UI should distinguish:

```text
Received 10:42:01
AI completed 10:42:05
```

rather than pretending the event arrived only after AI completed.

---

# 133. Live Feed Update

Example:

```text
10:42:01
TRUMP
New alert received
AI analysis: Processing...

10:42:05
TRUMP
New statement raises uncertainty
AI analysis: Completed
```

---

# 134. Source Badge

Each event should show its source.

Example:

```text
Gmail / Google Alerts
```

Future:

```text
RSS
News API
YouTube
Web
```

---

# 135. Topic Badge

Topic should be clearly visible:

```text
[TRUMP]
[IRAN]
[CELEBRITY X]
```

This helps scanning.

---

# 136. Priority + Topic + Time

The three most important metadata elements in the feed are:

```text
Priority
Topic
Time
```

They should be visible without opening the event.

---

# 137. AI Summary Length

Dashboard summary should normally be short:

```text
1–3 sentences
```

Detailed analysis belongs in the event view.

---

# 138. Popup Summary Length

Popup summary should be even shorter:

```text
1–2 sentences
```

The popup is for rapid awareness, not complete analysis.

---

# 139. Notification Title

Recommended format:

```text
[TOPIC] Headline
```

Example:

```text
[TRUMP] New statement raises uncertainty
```

Avoid extremely long titles.

---

# 140. Browser/Source Security

When opening external URLs:

- Validate URL scheme.
- Prefer HTTPS.
- Do not execute arbitrary local commands.
- Do not interpret email HTML as trusted application content.

---

# 141. HTML Email Rendering

Raw HTML emails should be sanitized.

Potentially dangerous content should not be allowed to execute arbitrary scripts inside the application.

---

# 142. User Feedback

Actions should provide immediate feedback.

Example:

```text
Topic saved.
```

or:

```text
AI reprocessing queued.
```

Avoid silent button clicks.

---

# 143. Toast Messages

Short-lived toast messages can be used for non-critical feedback:

```text
Topic saved
Backup completed
AI reprocessing queued
Settings updated
```

Do not use toasts for critical failures.

---

# 144. Accessibility of Notifications

Desktop notifications should include meaningful text even if visual styling is unavailable.

---

# 145. Localization

The UI should be structured so that text can eventually be localized.

Hardcoded strings should be centralized where practical.

---

# 146. UI Component Library

A consistent internal component set should eventually include:

```text
StatusBadge
PriorityBadge
TopicBadge
EventCard
EventTable
SummaryPanel
NotificationPopup
SettingsSection
EmptyState
ErrorState
LoadingState
ConfirmDialog
```

---

# 147. Reusable Components

The same component should be reused across:

```text
Dashboard
Search
Topic detail
Story detail
Notifications
```

where the presentation semantics are the same.

---

# 148. Design System

Create a centralized design system for:

```text
Typography
Spacing
Borders
Radius
Icons
Status indicators
Priority indicators
Buttons
Inputs
Tables
Cards
Dialogs
```

This avoids visual inconsistency.

---

# 149. UI Acceptance Criteria

The initial UI is considered acceptable when:

```text
[ ] User can connect Gmail
[ ] User can see Gmail connection status
[ ] User can discover labels
[ ] User can create a topic
[ ] User can assign an AI profile
[ ] User can enable/disable topic
[ ] User can see live events
[ ] User can see AI summary
[ ] User can open details
[ ] User can open original source
[ ] Windows popup appears bottom-right
[ ] Popup fades/animates correctly
[ ] Popup can be dismissed
[ ] Notifications do not block the UI
[ ] History can be searched
[ ] System tray works
[ ] Application can continue monitoring while minimized
```

---

# 150. Future UI Acceptance Criteria

Future:

```text
[ ] Story timeline
[ ] AI profile editor
[ ] Rule editor
[ ] Attachment viewer
[ ] Content generation
[ ] YouTube script review
[ ] Video generation
[ ] Publishing workflow
```

---

# 151. Recommended MVP Screens

The first implementation should focus on:

```text
1. First Run / Gmail Setup
2. Dashboard
3. Intelligence Details
4. Topics
5. Topic Editor
6. Notifications
7. Settings
8. System Tray
```

Do not implement every future screen before the core workflow works.

---

# 152. First Vertical UI Slice

The first UI milestone should be:

```text
Start Application
      |
      v
Dashboard
      |
      v
Gmail Connected
      |
      v
Topic Enabled
      |
      v
Real-Time Event
      |
      v
AI Summary
      |
      v
Bottom-right Popup
      |
      v
Details
```

This should be demonstrated before expanding the UI.

---

# 153. AI Coding Agent UI Rules

Any AI coding agent modifying the UI must:

1. Read this document.
2. Reuse the design system.
3. Avoid hardcoded business rules in widgets.
4. Keep network calls outside the GUI thread.
5. Use application use cases.
6. Use view models/DTOs.
7. Preserve accessibility.
8. Preserve dark/light/system themes.
9. Avoid creating duplicate UI components.
10. Add tests for non-trivial UI logic.
11. Never silently change navigation or interaction behavior.
12. Document significant UX changes.

---

# 154. UI Anti-Patterns

Avoid:

```text
Huge settings window
One giant dashboard
Raw email as the primary view
AI output without source context
Blocking dialogs for normal operations
Blocking network calls
Tables with excessive columns
Color-only status
Hardcoded topic names
Hardcoded notification text
Business logic in widgets
Direct SQL from UI
Direct Gmail SDK from UI
```

---

# 155. Final UX Model

The application should feel like:

```text
                INSIGHTFLOW AI

       "Something important just happened."

                      ↓

             AI understands it.

                      ↓

           "Here is what matters."

                      ↓

             "Here is why."

                      ↓

          "Here is what to watch."

                      ↓

              "Here is the source."

                      ↓

           User decides what to do.
```

The application should **inform the user, not make trading decisions for the user**.

---

# 156. Final UI Principle

The most important UX rule is:

> **The user should be able to understand an important event in approximately five seconds without opening the original email.**

The user can then choose to go deeper:

```text
5-second understanding
       ↓
30-second analysis
       ↓
Full source investigation
       ↓
Future action/content creation
```

This principle should guide every future UI decision.
