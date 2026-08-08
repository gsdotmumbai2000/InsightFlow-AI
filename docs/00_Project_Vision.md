# InsightFlow AI — Project Vision

**Document:** `00_Project_Vision.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08

---

## 1. Vision

InsightFlow AI is a desktop-first, AI-powered intelligence and content automation platform designed to continuously collect information from configurable sources, understand and summarize that information using AI, identify what is important to the user, deliver timely notifications, preserve an intelligent history, and eventually transform selected information into publishable multimedia content.

The platform is intentionally **source-agnostic and topic-agnostic**.

It must not be hardcoded for Trump, Iran, markets, celebrities, technology, or any other specific subject. The user defines what they want to monitor and how the information should be analyzed.

The long-term goal is:

> **Turn information overload into timely, understandable, actionable intelligence and reusable content.**

---

## 2. The Problem

Modern information arrives continuously from many sources:

- Google Alerts
- Email
- News feeds
- RSS
- Websites
- YouTube
- Social platforms
- Government announcements
- Company announcements
- Financial and market information
- Documents and attachments

The problem is not lack of information. The problem is:

1. Too much information.
2. Repeated and duplicate information.
3. Important information mixed with noise.
4. Difficulty identifying what has actually changed.
5. Lack of time to read every article.
6. Difficulty understanding the significance of an event.
7. Difficulty converting useful information into reusable content.

For a trader, for example, a breaking geopolitical development may be relevant within minutes. For another user, the same platform may be used to monitor a celebrity, company, technology, government policy, or any other subject.

InsightFlow AI exists to solve this information-processing problem.

---

## 3. Core Philosophy

The application must follow these principles:

### 3.1 User Defines the Subject

The application must never assume what the user considers important.

Examples:

- TRUMP
- IRAN-US
- MODI
- RBI
- FED
- NIFTY
- NVIDIA
- OPENAI
- A specific celebrity
- A sports team
- A company
- A research topic

Any topic should be possible.

### 3.2 Source and Topic Are Independent

A topic must not be tightly coupled to one source.

For example:

```text
Topic: TRUMP

Sources:
    Gmail
    RSS
    Web
    YouTube
```

Likewise:

```text
Source: Gmail Label

Labels:
    TRUMP
    IRAN
    MODI
    CELEBRITY
```

The architecture must allow additional sources later.

### 3.3 AI Behavior Is Configurable

Different topics require different analysis.

A trading topic may require:

- Market impact
- Asset impact
- Direction
- Risk
- Confidence

A celebrity topic may require:

- What happened
- Career impact
- New movie
- Controversy
- Public reaction

Therefore AI instructions must be configurable per topic/profile.

### 3.4 Real-Time First

The system should use event-driven mechanisms wherever the source supports them.

For Gmail, the preferred architecture is Gmail push notifications through Google Cloud Pub/Sub rather than periodic polling.

The goal is near-real-time awareness, not a 30-second or 60-second polling cycle.

### 3.5 Human Decision Remains Important

The application is an intelligence and decision-support system.

It must not represent AI analysis as certainty.

For trading-related analysis, it should clearly distinguish:

- Facts
- AI interpretation
- Potential implications
- Uncertainty
- Confidence

The application must never present AI output as a guaranteed trading prediction.

---

## 4. Primary Use Case

The initial real-world use case is monitoring Google Alerts delivered into Gmail.

Example:

```text
Google Alert
      |
      v
Gmail
      |
      v
Configured Gmail Label
      |
      v
InsightFlow AI
      |
      +--> Extract content
      |
      +--> Detect duplicate / related information
      |
      +--> AI analysis
      |
      +--> Store intelligence
      |
      +--> Desktop notification
      |
      +--> Optional attachment processing
      |
      +--> Optional content generation
```

The Gmail label is the initial input mechanism, not the permanent limitation of the platform.

---

## 5. AI Intelligence Pipeline

A received item should pass through a controlled pipeline.

```text
INGEST
   |
   v
NORMALIZE
   |
   v
CLASSIFY
   |
   v
DEDUPLICATE
   |
   v
UNDERSTAND
   |
   v
SUMMARIZE
   |
   v
ANALYZE
   |
   v
PRIORITIZE
   |
   v
NOTIFY
   |
   v
STORE
   |
   v
OPTIONAL CONTENT GENERATION
```

### Ingest

Receive information from a configured source.

### Normalize

Convert source-specific information into a common internal document/event model.

### Classify

Determine topic, category, entities, importance, and applicable processing rules.

### Deduplicate

Identify repeated or substantially similar information.

### Understand

Extract facts, entities, dates, claims, events, and relationships.

### Summarize

Generate a concise AI summary.

### Analyze

Apply the topic-specific AI instructions.

### Prioritize

Determine whether the information requires immediate attention.

### Notify

Present an appropriate desktop notification.

### Store

Persist the original metadata, AI analysis, and processing history.

### Content Generation

Optionally generate scripts, titles, descriptions, thumbnails concepts, narration, and video assets.

---

## 6. Desktop Notification Vision

The application will run primarily as a Windows desktop application and may operate quietly in the system tray.

Important information should appear as a modern notification in the bottom-right corner of the Windows desktop.

Expected behavior:

- Slide/fade into view.
- Remain visible for a configurable period.
- Fade out automatically.
- Support multiple notifications.
- Support priority levels.
- Allow the user to open the original source.
- Show concise AI-generated information.
- Avoid interrupting the user unnecessarily.

Example:

```text
+------------------------------------------+
| 🚨 HIGH IMPACT                           |
|                                          |
| Trump issues new statement on Iran       |
|                                          |
| AI Summary                               |
| Diplomatic pressure has increased...     |
|                                          |
| Potential Impact                         |
| Oil ↑   Gold ↑   Equities: Volatile      |
|                                          |
| [Open] [Details] [Dismiss]               |
+------------------------------------------+
```

The exact visual design will be defined in the UI/UX documentation.

---

## 7. Topic Model

A topic is a user-defined monitoring context.

Example:

```text
Topic
    Name: TRUMP
    Source: Gmail
    Label: TRUMP
    AI Profile: Trading / Geopolitics
    Priority: High
    Notifications: Enabled
    Content Generation: Enabled
```

Another:

```text
Topic
    Name: CELEBRITY_X
    Source: Gmail
    Label: CELEBRITY_X
    AI Profile: Entertainment
    Priority: Medium
    Notifications: Enabled
    Content Generation: Disabled
```

No source-specific or topic-specific business logic should be embedded in the core application.

---

## 8. AI Summary as a First-Class Capability

AI summarization is mandatory for the primary processing pipeline.

The summary should be more than a shortened copy of the email.

It should answer, where applicable:

- What happened?
- Who is involved?
- What changed?
- Why does it matter?
- What is confirmed?
- What is uncertain?
- What should the user watch next?

Topic-specific analysis can extend this.

For trading-related topics, for example:

- Potential market impact
- Potentially affected assets
- Possible bullish/bearish/volatile bias
- Key risks
- Important follow-up events
- Confidence level

---

## 9. Attachment Processing

Attachment processing is optional.

Supported examples may include:

- PDF
- Excel
- CSV
- Word
- ZIP
- Images

The user must control whether attachments are downloaded and/or processed.

Where technically appropriate, the platform should support analyzing attachment contents without permanently saving the original file.

Attachment processing must be isolated from the core intelligence pipeline so it can be enabled or disabled independently.

---

## 10. Knowledge and History

InsightFlow AI should maintain a searchable history of processed information.

The system should eventually allow the user to ask questions such as:

- What changed about Iran today?
- What were the major Trump developments this week?
- Show me all high-impact events from today.
- Has this event already been reported?
- What developments happened before this announcement?
- Summarize the evolution of this story.

The system should preserve relationships between related events so that a developing story can be viewed as a timeline rather than isolated emails.

---

## 11. Future Content Creation

One of the major long-term goals is converting selected AI intelligence into YouTube content.

Example:

```text
Incoming Information
        |
        v
AI Summary
        |
        v
Story / Event Analysis
        |
        v
YouTube Script
        |
        v
Narration
        |
        v
Images / Video Assets
        |
        v
3-Minute Video
        |
        v
Thumbnail + Metadata
        |
        v
User Review
        |
        v
YouTube Upload
```

The initial implementation should not attempt to build the complete video pipeline immediately.

However, the architecture must preserve the information and metadata required to support it later.

---

## 12. Human Approval

Content publishing should initially require explicit human approval.

The long-term system may support configurable automation levels:

```text
Manual
    |
    v
AI prepares content
    |
    v
User approves
    |
    v
Publish
```

Later:

```text
Trusted Topic
    |
    v
AI generates content
    |
    v
Automatic publishing
```

Automatic publishing must be an explicit user configuration, not the default.

---

## 13. Long-Term Source Architecture

The first implementation will prioritize Gmail.

Future sources may include:

- Gmail
- Outlook
- RSS
- News APIs
- Websites
- YouTube
- Social platforms
- Telegram
- Local folders
- Google Drive
- Other APIs
- User-provided documents

All sources should map into a common internal model.

Conceptually:

```text
                    +--> Gmail
                    |
                    +--> RSS
                    |
                    +--> Web
                    |
                    +--> YouTube
                    |
Sources ------------+
                    |
                    +--> Documents
                    |
                    +--> APIs
                    |
                    +--> Future Sources
                    |
                    v
              Common Event Model
                    |
                    v
              AI Intelligence
```

---

## 14. Long-Term AI Provider Architecture

The first AI provider may be AWS Bedrock with Claude.

The application must not be permanently coupled to one AI vendor.

The architecture should support:

```text
AI Provider Interface
        |
        +--> AWS Bedrock
        |
        +--> OpenAI
        |
        +--> Gemini
        |
        +--> Ollama / Local Models
        |
        +--> Future Providers
```

Provider-specific code belongs in infrastructure/adapters, not in the domain layer.

---

## 15. Privacy and Security Vision

The platform may process potentially sensitive emails and documents.

Therefore:

- Credentials must never be stored in source code.
- OAuth tokens must be protected.
- Secrets must be stored securely.
- Logs must not accidentally expose sensitive content.
- AI provider usage must be configurable.
- Local data storage must be protected where appropriate.
- Users must know what information is sent to external AI providers.
- Data retention must be configurable.
- Destructive operations require explicit authorization.

---

## 16. Reliability Vision

The system must be resilient to:

- Temporary Gmail failures.
- Pub/Sub delivery delays.
- Network failures.
- AI provider failures.
- Rate limits.
- Invalid emails.
- Malformed attachments.
- Duplicate notifications.
- Application restarts.

Important events must not silently disappear.

The processing pipeline should support:

- Idempotency
- Retry
- Dead-letter/error handling
- Processing states
- Audit history
- Structured logging

---

## 17. Extensibility Vision

New functionality should be added through well-defined interfaces.

Examples:

```text
New Source
New AI Provider
New Notification Provider
New Attachment Processor
New Content Generator
New Publishing Provider
New Workflow Action
New Rule
```

The core domain should not require major modification when these capabilities are added.

---

## 18. Product Evolution

### Phase 1 — Intelligence Inbox

- Gmail integration
- Gmail label monitoring
- Real-time notifications
- AI summaries
- Topic configuration
- Local history

### Phase 2 — Intelligence Platform

- Multiple labels/topics
- Deduplication
- Story grouping
- Timeline
- Search
- AI chat
- Rules engine
- Attachment analysis

### Phase 3 — Content Studio

- AI script generation
- YouTube title/description
- Thumbnail concepts
- Voice generation
- Image/video generation
- Video composition

### Phase 4 — Publishing Automation

- YouTube integration
- Scheduled publishing
- Approval workflow
- Metadata optimization
- Publishing history

### Phase 5 — Multi-Source Intelligence Platform

- RSS
- News APIs
- Websites
- YouTube
- Social sources
- Other enterprise sources

---

## 19. What InsightFlow AI Is NOT

The platform is not intended to be:

- A hardcoded Trump news application.
- A hardcoded Iran-US monitoring application.
- A dedicated trading signal generator.
- A replacement for professional financial advice.
- A generic email client.
- A simple Gmail notification script.
- A system that blindly republishes AI-generated content.

The platform is a configurable **information intelligence and automation engine**.

---

## 20. Success Criteria

The initial product should satisfy the following:

1. A user can configure a Gmail label.
2. New information can be detected with near-real-time delivery.
3. The information is processed automatically.
4. AI generates a useful summary.
5. The summary is displayed through a desktop notification.
6. The user can configure different topics independently.
7. Different topics can use different AI instructions.
8. Duplicate/repetitive information can be identified.
9. Processed information is searchable later.
10. Attachments can be optionally processed.
11. The architecture does not depend on a single topic.
12. The architecture does not depend permanently on Gmail.
13. The architecture does not depend permanently on one AI provider.
14. Future YouTube content generation can be added without redesigning the core.

---

## 21. Guiding Principle

The most important design principle of InsightFlow AI is:

> **The platform should process information according to the user's intent, not according to assumptions built into the software.**

The user defines:

```text
WHAT to monitor
      +
WHERE to get it
      +
HOW AI should understand it
      +
WHEN to notify
      +
WHAT action should follow
```

InsightFlow AI provides the infrastructure that connects these pieces into a reliable, extensible intelligence pipeline.

---

## 22. Final Vision Statement

> **InsightFlow AI transforms continuous streams of information into personalized intelligence, timely awareness, and reusable content.**
>
> It begins with Gmail and AI-powered summaries, but its architecture is designed to evolve into a multi-source intelligence and content automation platform.
>
> The user remains in control of what is monitored, how it is interpreted, and what actions are taken. AI provides the intelligence layer that makes large volumes of information understandable and useful.

---

## Document Governance

This document defines the long-term vision.

It should change relatively rarely.

Detailed technical decisions belong in:

- Product Requirements
- Architecture
- System Design
- ADRs
- AI Development Guide
- UI/UX Design
- Database Design
- Implementation documentation

If implementation decisions conflict with this vision, the conflict must be explicitly documented and reviewed rather than silently changing the product direction.
