# InsightFlow AI — Phase 9 Email → IntelligenceEvent Notes

**Document:** `16_Phase9_Email_To_IntelligenceEvent_Notes.md`
**Status:** Implemented
**Parent Documents:** `06_Database_Design.md`, `10_Interface_and_API_Contracts.md`, `13_Implementation_Roadmap.md`, `15_Phase8_Gmail_Message_Retrieval_Notes.md`

---

## 1. Scope

Phase 9 converts Phase 8's normalized `EmailMessageDto` into persisted,
provider-neutral `IntelligenceEvent` (+ `Attachment` metadata) domain
records, with idempotent deduplication. It deliberately stops short of:

- Gmail Watch / Google Cloud Pub/Sub / real-time push (a later phase).
- AI summarization/analysis.
- Priority calculation, notifications, story grouping.
- Attachment downloading (metadata only, as in Phase 8).

This phase's own scope was inferred from the roadmap and the explicit
boundary comments left in Phase 8's implementation ("no IntelligenceEvent —
that is Phase 9") rather than a fresh detailed spec; see §8 for the
resulting design decisions that are worth a second look.

---

## 2. What's new

| Layer | Addition |
|---|---|
| Application DTO | `IngestTopicMessagesRequest`, `IngestedEventDto`, `IngestTopicMessagesResult` (`application/dto/email.py`) |
| Application use case | `IngestTopicMessagesUseCase` (`application/commands/gmail.py`) |
| Application helpers | `_email_message_to_create_event_request`, `_normalize_content`, `_strip_html`, `_compute_content_hash`, `_gmail_permalink` (same module) |
| Wiring | `ApplicationUseCases.ingest_topic_messages`, built in `use_cases.build_use_cases` |
| UI | "Save recent messages" button on the Topics page (background `QThread`, mirrors Phase 8's "Retrieve recent messages") |

No domain, infrastructure, or database schema changes were required — the
`IntelligenceEvent`/`Attachment` entities, their repositories, and
`CreateIntelligenceEventUseCase` already existed (Phase 3–5) and are reused
as-is.

---

## 3. Composition, not reimplementation

`IngestTopicMessagesUseCase` does not reimplement retrieval, pagination, or
event persistence. It composes two existing use cases:

```
IngestTopicMessagesUseCase
    -> RetrieveTopicMessagesUseCase.execute(...)   (Phase 8: retrieval, MIME
                                                     normalization, per-message
                                                     resilience)
    -> CreateIntelligenceEventUseCase.execute(...) (Phase 5: creation +
                                                     idempotent dedup via
                                                     source_id + external_id)
```

`build_use_cases` constructs both dependencies once and injects the same
instances into `IngestTopicMessagesUseCase`, so retrieval logic and
event-creation/dedup logic each have exactly one implementation.

---

## 4. Gmail → `CreateIntelligenceEventRequest` mapping

| `CreateIntelligenceEventRequest` field | Source |
|---|---|
| `source_type` | `"GMAIL"` |
| `source_id`, `account_id` | Topic's `SourceConfiguration.source_id` (the connected Gmail account id) |
| `external_id` | `EmailMessageDto.external_message_id` |
| `thread_id` | `EmailMessageDto.thread_id` |
| `topic_id` | The Topic being ingested for |
| `url` | Constructed Gmail permalink: `https://mail.google.com/mail/u/0/#all/{message_id}` |
| `title` | `EmailMessageDto.subject` |
| `normalized_content` | `text_body` preferred; falls back to a lightweight HTML-to-text extraction of `html_body`; `None` if neither exists |
| `source_published_at` | `EmailMessageDto.received_at` (Gmail's `internalDate`-derived canonical timestamp) |
| `content_hash` | SHA-256 hex of `normalized_content`, or `None` if there is no content |
| `received_at` | **Left unset.** `IntelligenceEvent.create()` then defaults it to ingestion time, deliberately distinct from `source_published_at` (when Gmail says the message arrived vs. when InsightFlow processed it) |
| `priority` | Not set — the priority engine is a later phase |

### HTML fallback

`_strip_html` is a small, dependency-free `html.parser.HTMLParser` subclass:
it drops `<script>`/`<style>` content and collects the remaining text nodes.
It never raises (feed errors are caught and produce an empty string) and
performs no aggressive normalization beyond whitespace collapsing — matching
Phase 8's explicit deferral ("do not perform aggressive HTML-to-text
transformation... unless required," now required because `normalized_content`
needs *some* text when only HTML exists).

---

## 5. Deduplication

Deduplication is **not reimplemented** in this phase. It's the existing
`source_id + external_id` uniqueness that `CreateIntelligenceEventUseCase`
already enforces (`IntelligenceEventRepository.find_by_external_id`, backed
by a unique constraint in SQLite). `IngestTopicMessagesUseCase` catches
`DuplicateEventError` per message and increments `duplicate_count` instead
of treating it as a failure — re-running ingestion for the same label is
therefore always safe and produces zero new records for messages already
stored.

This is Level 1 deduplication only (external ID), per
`06_Database_Design.md` §17. `content_hash` is computed and persisted so a
future phase can add Level 2 (content-hash) deduplication without a schema
change.

---

## 6. Attachments

For each successfully created event, non-inline `EmailAttachmentDto` entries
(`is_inline is False`) become `Attachment` domain records
(`filename`, `content_type`, `size_bytes`, `external_id` — metadata only,
still never downloaded). Inline attachments (e.g. signature images, tracked
via `is_inline=True` in Phase 8's MIME parsing) are **not** persisted as
`Attachment` records, since they aren't meaningful user-facing attachments —
this mirrors the Phase 8 documentation's distinction between "attachment"
and "inline content." Attachment persistence happens in its own short
transaction, separate from the event-creation transaction (per
`06_Database_Design.md` §59: "keep transactions short").

---

## 7. Domain events, logging, and privacy

- For every newly created (non-duplicate) event,
  `IngestTopicMessagesUseCase` appends an `IntelligenceEventCreated` domain
  event (`domain/events/__init__.py`) to `IngestTopicMessagesResult.domain_events`.
  No dispatch/bus exists yet — consistent with `DomainEventCollector`'s own
  docstring ("Phase 5 does not dispatch") — this only makes the event
  observable/testable for a future consumer (e.g. a notification or story
  service) to drain.
- Logging is limited to `topic_id`, `label_id`, requested/created/duplicate/
  failed counts, and elapsed milliseconds — never subject, sender, or body
  content (verified by test).
- `FailedMessageDto.error_message` carries the translated application error
  text, not raw content.

---

## 8. Design decisions worth a second look

Because this phase started from a one-line request ("Phase 9 — Email →
IntelligenceEvent") rather than a detailed spec like Phase 8's, the
following interpretations were made and should be confirmed:

1. **Scope boundary.** Real-time Watch/Pub/Sub, AI analysis, priority, and
   notifications were treated as out of scope, based on Phase 8's own
   deferral comments and the roadmap. If "Phase 9" was meant to include
   more (e.g. wiring this into a scheduled/background poll rather than a
   manual button), that wasn't built.
2. **UI: separate button, not a merge.** "Retrieve recent messages" (Phase
   8, preview-only, no persistence) and "Save recent messages" (Phase 9,
   persists) are two distinct buttons rather than one button with changed
   behavior, to avoid changing Phase 8's already-tested UI contract. This
   does mean the Topics page now has two very similar-looking actions —
   acceptable for a debug/manual-test UI at this stage (per the roadmap,
   the real end-user UI is Phase 14's Dashboard/Intelligence views), but
   worth revisiting once a real UI is built.
3. **Inline attachments dropped, not flagged.** Rather than persisting
   inline images with an `is_inline` marker (the `Attachment` domain entity
   has no such field today), they're simply not persisted. Adding the field
   would touch the stable `Attachment` entity/schema; deferred until there's
   a concrete need to inspect inline content.
4. **`account_id` re-fetch.** `IngestTopicMessagesUseCase` re-fetches the
   Topic (one extra cheap read) rather than extending
   `RetrieveTopicMessagesResult` with an `account_id` field, to avoid
   modifying Phase 8's tested contract for a single caller's convenience.
5. **Domain event collection without a bus.** `IntelligenceEventCreated` is
   populated but has no consumer yet. This is speculative in the sense that
   nothing drains it today; it was included because it's essentially free
   (reuses an existing, unused domain-event type) and makes intent explicit
   for whichever phase adds notifications/story-grouping next.

---

## 9. Testing

- `tests/unit/application/test_gmail_ingestion.py` — normalization helpers
  (HTML stripping, content-hash determinism, field mapping) and the full
  `IngestTopicMessagesUseCase`: topic validation, event creation + field
  correctness, idempotent re-run (0 new, all duplicate), non-inline-only
  attachment persistence, malformed-message resilience (batch continues),
  `has_more` bounding, and a privacy test asserting body content never
  appears in logs.
- `tests/unit/presentation/test_topics_ui.py` — `test_save_recent_messages_persists_events_and_summarizes`
  verifies the new button persists events, summarizes the result, and that
  re-running reports "0 new... already stored" rather than duplicating.
- No new architecture-boundary or infrastructure tests were needed — no new
  infrastructure or domain code was added.

All automated tests run against fakes (`FakeGmailAdapter`, in-memory
`InMemoryStore`/real `SQLiteUnitOfWork` used elsewhere) — no network, no
real Gmail credentials. A live-account manual test was not re-run for this
phase since it persists to the same local SQLite database Phase 8 already
proved reachable; if you want to verify manually: connect Gmail, select a
Gmail-mapped Topic, click **Save recent messages**, then reopen and click it
again to confirm the summary changes from "Saved N new event(s)" to "Saved 0
new event(s), N already stored."

---

## 10. Deferred to later phases

- Gmail Watch / Pub/Sub / `history.list` real-time triggering.
- AI summarization and structured analysis (`AIAnalysis`).
- Priority engine, notification policy, desktop popups.
- Story grouping / content-hash-based (Level 2+) deduplication.
- Dispatching `IntelligenceEventCreated` to real consumers.
- Any UI beyond the manual test button (Dashboard/Intelligence views).
