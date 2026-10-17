# InsightFlow AI — Phase 8 Gmail Message Retrieval Notes

**Document:** `15_Phase8_Gmail_Message_Retrieval_Notes.md`
**Status:** Implemented
**Parent Documents:** `10_Interface_and_API_Contracts.md`, `11_Gmail_RealTime_Monitoring_Design.md`, `13_Implementation_Roadmap.md`

---

## 1. Scope

Phase 8 adds the Gmail **message retrieval and normalization** foundation:
listing messages for a Topic's mapped Gmail label, retrieving individual
messages, parsing MIME structure, and producing a provider-neutral
`EmailMessageDto`. It deliberately stops short of Gmail Watch/Pub/Sub
(Phase 10), AI analysis (Phase 11/12), and `IntelligenceEvent` creation
(Phase 9) — those are out of scope here.

---

## 2. Gmail API calls used

| Operation | Method | Notes |
|---|---|---|
| List message IDs for a label | `users.messages.list` | Filtered by `labelIds=[label_id]`; `maxResults` capped at 500 (Google's documented per-call maximum); paginated via `pageToken`/`nextPageToken`. |
| Retrieve a message | `users.messages.get` | `format=full` — required to extract MIME body/attachment metadata. `RAW` is intentionally not used. |

Both calls live only in `infrastructure/gmail/adapter.py` (`GoogleGmailAdapter`).
No other layer imports `googleapiclient`.

---

## 3. Gmail port changes

`application/ports/gmail.py` gained a third small Protocol alongside the
existing `GmailAuthenticator` and `GmailLabelProvider`:

```python
class GmailMessageProvider(Protocol):
    def list_message_ids(self, request: ListGmailMessagesRequest) -> GmailMessageListPageDto: ...
    def get_message(self, message_id: str) -> EmailMessageDto: ...
```

`GoogleGmailAdapter` implements all three Protocols (same pattern already
established in Phase 7), reusing its existing `_require_valid_credentials()`
helper rather than duplicating OAuth/credential plumbing in a second class.

---

## 4. Message DTO (`application/dto/email.py`)

`EmailMessageDto` is a provider-neutral, immutable dataclass — **not** a
domain entity (see §9). Fields: `provider`, `external_message_id`,
`thread_id`, `subject`, `sender`, `recipients`, `cc`, `bcc`, `reply_to`,
`message_id_header`, `in_reply_to`, `references`, `received_at`
(from `internalDate`), `date_header` (original `Date` header, preserved
separately), `snippet`, `text_body`, `html_body`, `label_ids`,
`attachments`, `size_estimate`, `history_id`, `content_truncated`.

Supporting types: `EmailAddressDto` (display name + email), `EmailAttachmentDto`
(metadata only — filename, mime_type, attachment_id, size_estimate,
is_inline, content_id), `ListGmailMessagesRequest` / `GmailMessageListPageDto`
/ `GmailMessageRefDto` (listing + pagination), and
`RetrieveTopicMessagesRequest` / `RetrieveTopicMessagesResult` /
`FailedMessageDto` (the bounded application-level retrieval contract).

---

## 5. MIME parsing strategy (`infrastructure/gmail/mime.py`)

Gmail's `messages.get(format=FULL)` response already parses the raw RFC 5322
message into a JSON `payload`/`parts` tree, so parsing walks that tree
recursively rather than re-parsing raw bytes:

- `multipart/*` parts (and any part carrying `parts`) are traversed into
  their children.
- A leaf part with **no filename and no attachment ID** whose `mimeType` is
  `text/plain` or `text/html` becomes body content. `text/plain` and
  `text/html` parts are each concatenated in encounter order (Gmail rarely
  sends more than one of each real body); nothing is duplicated between
  `text_body`/`html_body` and the `attachments` list.
- A leaf part **with a filename or an attachment ID** becomes attachment
  metadata (§7) — regardless of its declared MIME type, matching Gmail's own
  attachment-detection behavior.
- Header lookup is case-insensitive per part (`headers_map`).

Standard-library `email` facilities do the RFC-5322-adjacent work rather
than a custom parser:

- `email.utils.getaddresses` — address-list parsing (`From`/`To`/`Cc`/`Bcc`/`Reply-To`), including multiple recipients and quoted display names.
- `email.header.decode_header` — RFC 2047 encoded-word decoding (e.g. non-ASCII display names).
- `email.utils.parsedate_to_datetime` — the original `Date` header.
- `email.message.Message` — charset extraction from a part's `Content-Type` header (`get_content_charset()`).

## 6. Header parsing

Extracted (case-insensitively): `From`, `To`, `Cc`, `Bcc`, `Reply-To`,
`Subject`, `Date`, `Message-ID`, `References`, `In-Reply-To`. Missing headers
map to `None` / empty tuples rather than raising — every field in
`EmailMessageDto` that corresponds to an optional header is `Optional` or an
empty tuple by default.

## 7. Attachment vs. inline vs. body

A leaf part is classified as an attachment (in `EmailMessageDto.attachments`)
whenever it carries a `filename` or a Gmail `body.attachmentId`. Within that,
`is_inline` is set when the part's `Content-Disposition` says `inline`, or it
carries a `Content-ID` without an explicit `attachment` disposition — the
typical shape of an inline image inside `multipart/related`. Consumers can
filter `is_inline` attachments out of a "real" attachment list without the
retrieval layer silently discarding that information.

**No attachment bytes are ever downloaded or written to disk in this phase.**

## 8. Date handling

- `received_at` is derived from Gmail's `internalDate` (epoch milliseconds),
  converted to timezone-aware UTC — this is the canonical ordering timestamp
  per Google's documented behavior (more reliable than the `Date` header for
  normally-delivered SMTP mail).
- `date_header` preserves the original `Date` header, parsed independently
  and also converted to aware UTC; parsing failures yield `None` rather than
  raising or fabricating a naive datetime.
- No naive `datetime` is ever constructed.

## 9. Domain boundary

`EmailMessageDto` is an **application-layer DTO**, not a domain entity. Phase
8 does not create `IntelligenceEvent` records and does not extend the
`Attachment` domain entity (which is keyed by `EventId` and belongs to the
Phase 9 event pipeline). This mirrors the roadmap's explicit instruction to
keep the Gmail→`IntelligenceEvent` transformation decision for the next
phase.

## 10. Pagination and retrieval limits

- `GmailMessageListPageDto.next_page_token` mirrors Gmail's `nextPageToken`;
  `RetrieveTopicMessagesUseCase._collect_message_refs` pages through
  `messages.list` until either the bounded limit is reached or Gmail reports
  no further pages.
- `GoogleGmailAdapter.list_message_ids` caps `maxResults` at
  `GMAIL_LIST_MAX_RESULTS = 500` (Google's documented per-call maximum)
  regardless of what the caller requests.
- `RetrieveTopicMessagesUseCase` caps the total requested messages at
  `HARD_MAX_MESSAGES = 500` regardless of caller input, and always requests
  one extra reference beyond the caller's limit so it can report
  `has_more=True` and stop cleanly instead of silently truncating.
- Retrieval is strictly bounded: nothing resembling "retrieve the entire
  mailbox" exists in this phase.

## 11. Malformed-message resilience

- MIME parsing failures for a single message never abort a retrieval batch.
  `GoogleGmailAdapter.get_message` wraps `map_gmail_message_to_dto(...)` in a
  broad `try/except`, translating any parsing failure into
  `GmailMessageParsingError` (a `GmailError` subtype).
- `RetrieveTopicMessagesUseCase.execute` catches `GmailError` per message,
  logs a safe (no-content) warning, and records a `FailedMessageDto` — the
  remaining messages in the batch are still retrieved.
- A message body larger than the configured safety limit
  (`DEFAULT_MAX_BODY_BYTES = 2 MB`, see §12) is truncated per-part with
  `content_truncated=True` rather than silently dropped or allowed to grow
  memory unbounded.

## 12. Safety limits

| Limit | Value | Configurable via |
|---|---|---|
| Per-message body bytes accumulated before truncation | 2 MB (`mime.DEFAULT_MAX_BODY_BYTES`) | Constructor/function parameter (`max_body_bytes`) on `map_gmail_message_to_dto` / `extract_content`. |
| Gmail `messages.list` page size | 500 (`adapter.GMAIL_LIST_MAX_RESULTS`) | Fixed at Google's documented API maximum. |
| Total messages per `RetrieveTopicMessagesUseCase` call | 500 (`commands.gmail.HARD_MAX_MESSAGES`) | Hard ceiling; caller supplies a smaller `max_messages` (default request field value: 50). |
| Manual UI test retrieval | 5 messages | `topics_view_model.MANUAL_RETRIEVAL_MAX_MESSAGES`. |

These are documented constants rather than a new typed configuration
section, to avoid expanding `configuration/` for a bounded, code-level
safety limit — consistent with keeping this phase's footprint minimal.

## 13. Error translation

`infrastructure/gmail/errors.py` (`raise_translated_google_error`) gained a
`404 → GmailMessageNotFoundError` branch alongside the existing
401/403/429/5xx → `GmailReauthenticationRequiredError` /
`GmailAuthorizationError` / `GmailRateLimitError` / `GmailUnavailableError`
translations. New application-level Gmail errors:

- `TopicNotGmailConfiguredError` — the Topic's `SourceConfiguration` is not
  `GMAIL` (raised by the use case, not the adapter).
- `GmailMessageNotFoundError` — HTTP 404 / "not found" from Google, or an
  invalid message ID.
- `GmailMessageParsingError` — MIME normalization failed for a specific
  message.

All three are `GmailError` subclasses, so the existing presentation error
mapper (`presentation/errors.py`) already renders them without changes.

## 14. Application use case

`RetrieveTopicMessagesUseCase` (`application/commands/gmail.py`):

```
Topic ID → Topic (must exist) → SourceConfiguration (must be GMAIL)
        → GmailAuthenticator.get_account() (must be connected)
        → bounded messages.list pagination → messages.get per ID
        → EmailMessageDto[] + FailedMessageDto[] + has_more
```

It does not create `IntelligenceEvent` records. Logging is limited to
`topic_id`, `label_id`, requested/retrieved/failed counts, and elapsed
milliseconds — never subject, sender, or body content.

## 15. Privacy protections

- No email body, snippet, subject, or MIME payload is ever logged.
- Per-message failures log only `message_id` and the exception's type name
  (not the source content).
- `FailedMessageDto.error_message` carries the translated `GmailError`
  message text (e.g. "Gmail message X could not be found"), not raw
  provider payloads.
- The manual UI action displays only a retrieved/failed count summary — never
  message bodies — in the Topics page info banner.

## 16. Deferred to later phases

- Gmail Watch, Google Cloud Pub/Sub, `history.list` (Phase 10).
- `IntelligenceEvent` creation, deduplication, topic-resolution persistence
  (Phase 9).
- AI summarization/analysis (Phase 11/12).
- Attachment downloading/processing (future phase) — this phase captures
  attachment **metadata only**.
- Thread-level retrieval (`threads.get`) — only the individually selected
  message is retrieved; `thread_id` is preserved for later use.

## 17. Automated vs. live testing

All automated tests (`tests/unit/infrastructure/test_gmail_mime.py`,
`tests/unit/infrastructure/test_gmail_message_service.py`,
`tests/unit/application/test_gmail_retrieval.py`,
`tests/unit/presentation/test_topics_ui.py`) run against fixtures and a
monkeypatched `googleapiclient.discovery.build` / `FakeGmailAdapter` — no
network access, no real Google credentials. They do **not** prove the
integration against a live Gmail account; that requires the manual test in
§18, executed against a real, already-connected Gmail account.

## 18. Manual test (live Gmail account)

1. Start InsightFlow (`python -m insightflow`).
2. Open **Settings** and confirm Gmail shows `CONNECTED` (Phase 7). If not,
   connect Gmail first.
3. Open **Topics** and select the Topic mapped to the `TRUMP` label (or map
   one via Settings if it does not exist yet).
4. Click **Retrieve recent messages**. The button is only enabled when the
   selected Topic's source is `GMAIL`.
5. Confirm the info banner reports a retrieved-message count (e.g.
   "Retrieved 5 message(s).").
6. Verify the application window remains responsive while the retrieval is
   running (the call executes on a background `QThread`, not the GUI
   thread).
7. To inspect the retrieved data beyond the count summary, use a debugger or
   temporary breakpoint on `RetrieveTopicMessagesUseCase.execute` — the UI
   intentionally does not render raw message content in this phase — and
   confirm: message IDs are populated; subject/sender/date are extracted;
   `text_body`/`html_body` are present where the source email has them;
   attachment metadata (filename/mime_type/size) is populated for any
   message with attachments; no attachment file is written to disk anywhere
   under the application's data directory.
8. Disconnect and reconnect Gmail (Settings page), then repeat step 4 and
   confirm retrieval still succeeds.

Start with a small `max_messages` value — the UI action is hardcoded to 5
for this reason. Do not raise it to retrieve hundreds/thousands of messages
during first testing.

---

## 19. Design decisions worth reviewing

- `GmailMessageProvider` was added as a third Protocol on the existing
  `GoogleGmailAdapter` class (implementing `GmailAuthenticator +
  GmailLabelProvider + GmailMessageProvider`) rather than a separate
  infrastructure class, to reuse credential handling without duplicating it.
  If message retrieval grows substantially in a later phase, extracting a
  dedicated `GmailMessageService` collaborator (still behind the same port)
  is a reasonable follow-up.
- Retrieval limits are plain module constants with constructor/parameter
  overrides rather than new `GmailSettings`/environment-variable
  configuration, to keep this phase's configuration footprint minimal. If
  Phase 9+ needs these limits to be user-configurable, promote them to
  typed configuration then.
- The Topics page "Retrieve recent messages" button is a manual test/debug
  aid, not a designed end-user workflow — the real UI for browsing retrieved
  intelligence belongs to later phases (Dashboard/Intelligence views wired
  to `IntelligenceEvent`, Phase 9+).
