# InsightFlow AI — Phase 10 Gmail Real-Time Monitoring Notes

**Document:** `17_Phase10_Gmail_Realtime_Monitoring_Notes.md`
**Status:** Implemented
**Parent Documents:** `06_Database_Design.md`, `10_Interface_and_API_Contracts.md`,
`13_Implementation_Roadmap.md`, `15_Phase8_Gmail_Message_Retrieval_Notes.md`,
`16_Phase9_Email_To_IntelligenceEvent_Notes.md`

---

## 1. Scope

Phase 10 eliminates the need to manually click "Retrieve recent messages" /
"Save recent messages" for newly arriving Gmail messages. It adds:

- Gmail Watch (`users.watch`) registered against monitored labels.
- A desktop-side Google Cloud Pub/Sub subscriber (outbound `pull`/`acknowledge`
  only — no public HTTP endpoint, no port forwarding).
- Gmail History API (`users.history.list`) to turn a Pub/Sub notification into
  the specific messages that changed.
- Wiring from history results into **Phase 9's existing ingestion path** —
  no second ingestion implementation exists.

It deliberately stops short of: AI analysis, notifications/toasts, attachment
downloading, story grouping, and any script/video/YouTube functionality. See
§11.

---

## 2. Architecture

```
 Gmail account                     Google Cloud (your project)
 ┌────────────┐   users.watch      ┌───────────────────────────┐
 │   Gmail     │ ─────────────────▶│  Pub/Sub Topic             │
 │  (mailbox)  │  (label filter)   │  projects/P/topics/T       │
 └────────────┘                    └──────────────┬─────────────┘
        ▲                                          │ push-to-pull
        │ history.list / messages.get              ▼
        │                          ┌───────────────────────────┐
        │                          │  Pub/Sub Subscription      │
        │                          │  projects/P/subs/S         │
        │                          └──────────────┬─────────────┘
        │                                          │ pull() (outbound only)
        │                                          ▼
 ┌──────┴────────────────────────────────────────────────────────┐
 │  InsightFlow AI desktop process (Windows, no inbound ports)     │
 │                                                                  │
 │  GmailMonitoringWorker (threading.Thread, daemon)                │
 │    loop: renew watch if due -> subscriber.pull() -> for each msg:│
 │      parse_notification -> GmailPubSubNotificationProcessor      │
 │        -> GmailHistorySyncService.sync(start_history_id=cursor)  │
 │             -> history.list -> messages.get -> ingest_message()  │
 │                                   (Phase 9, existing, reused)     │
 │        -> advance monitoring_state cursor -> ack (only on success)│
 │                                                                  │
 │  monitoring_state (SQLite) ── durable cursor + status per account│
 └──────────────────────────────────────────────────────────────┘
```

Two independent OAuth-authorized identities exist side by side: Gmail
(`gmail.readonly`) and Pub/Sub (`pubsub`), see §5.

---

## 3. What's new

| Layer | Addition |
|---|---|
| Domain | `MonitoringStatus` enum, `MonitoringStateId`, `MonitoringState` entity (`domain/entities/monitoring_state.py`) |
| Database | `migrations/002_monitoring_state.sql`, `SQLiteMonitoringStateRepository`, `MonitoringStateRepository` port, `UnitOfWork.monitoring_states` |
| Application DTOs | `application/dto/monitoring.py` (`GmailWatchResultDto`, `GmailHistoryPageDto`, `PubSubNotificationDto`, `PubSubMessageDto`, `HistorySyncOutcome`, `MonitoringStatusDto`), `IngestMessageOutcome` (`application/dto/email.py`) |
| Application ports | `GmailWatchProvider`, `GmailHistoryProvider` (`ports/gmail.py`), `PubSubAuthenticator`, `PubSubSubscriber` (`ports/pubsub.py`) |
| Application exceptions | `GmailWatchError`, `GmailHistoryUnavailableError`, `GmailHistorySyncError`, `application/exceptions/pubsub.py`, `application/exceptions/monitoring.py` |
| Application services | `monitored_labels.py`, `gmail_history_sync.py`, `gmail_full_sync.py`, `gmail_watch_lifecycle.py`, `gmail_pubsub_processor.py`, `gmail_monitoring_worker.py`, `monitoring_worker_handle.py` |
| Application use cases | `ConnectPubSubUseCase`, `DisconnectPubSubUseCase`, `GetPubSubConnectionStatusUseCase`, `GetMonitoringStatusUseCase`, `StartMonitoringUseCase`, `StopMonitoringUseCase`, `RenewGmailWatchUseCase` (`application/commands/monitoring.py`) |
| Infrastructure | `GoogleGmailMonitoringAdapter` (Watch + History over `googleapiclient`), `infrastructure/pubsub/oauth.py`, `infrastructure/pubsub/adapter.py` (REST pull/ack), `infrastructure/pubsub/message_parser.py`, shared `oauth_client.py` |
| Configuration | `PubSubSettings`, new `INSIGHTFLOW_GMAIL_PUBSUB_*` / `INSIGHTFLOW_MONITORING_*` env vars |
| Presentation | Settings page "Real-time monitoring" section (status, Authorize/Revoke Pub/Sub, Start/Stop Monitoring, Renew Watch); Dashboard now shows the real persisted status |

Existing Phase 8/9 code — `RetrieveTopicMessagesUseCase`,
`IngestTopicMessagesUseCase.execute()`, `CreateIntelligenceEventUseCase` — is
**unchanged in behavior**. The one modification is
`IngestTopicMessagesUseCase.ingest_message()`, a new public method extracted
from the existing per-message logic inside `execute()` so both the manual
bulk path and the new real-time path share one implementation (see §4).

---

## 4. Reuse, not reimplementation

```
GmailHistorySyncService.sync(start_history_id)
    -> GmailHistoryProvider.list_history(...)     (new, Phase 10)
    -> GmailMessageProvider.get_message(...)       (Phase 8, reused as-is)
    -> IngestTopicMessagesUseCase.ingest_message()  (Phase 9 logic, now shared)
         -> CreateIntelligenceEventUseCase.execute() (Phase 5, dedup via
                                                        source_id+external_id)

GmailFullSyncService.sync_all_monitored_topics()
    -> IngestTopicMessagesUseCase.execute(...)      (Phase 9, unchanged —
                                                        the exact "Save recent
                                                        messages" path)
```

`ingest_message()` is the one place Gmail → `IntelligenceEvent` field
mapping, content-hash computation, deduplication, and attachment-metadata
persistence happen. `execute()` (the manual/bulk path) now simply loops and
calls it per message; this was verified not to change any Phase 8/9 test
behavior. Real-time processing never re-implements this mapping.

Dedup for real-time messages is the same Level-1 (`source_id + external_id`)
mechanism as Phase 9 — no new dedup logic was written. This also makes the
"watch established, then full sync" ordering (§7) and duplicate Pub/Sub
notification delivery (§9) safe: any overlap simply produces
`DuplicateEventError`, caught and counted, never a duplicate record.

---

## 5. Credential strategy: two separate OAuth authorizations

The existing Gmail OAuth (`gmail.readonly`) already can't request Pub/Sub
scope. The spec explicitly required avoiding a plaintext service-account key.
Given the existing OAuth/SecretStore infrastructure, the decision was:

- **Gmail OAuth** — unchanged, scope `gmail.readonly`, token key
  `insightflow.gmail.oauth.token`.
- **Pub/Sub OAuth** — a second, independent `InstalledAppFlow` consent using
  scope `https://www.googleapis.com/auth/pubsub`
  (`infrastructure/pubsub/oauth.py::PUBSUB_OAUTH_SCOPE`), stored under its own
  SecretStore key `insightflow.gmail.pubsub.oauth.token`
  (`infrastructure/secrets/keys.py::GMAIL_PUBSUB_OAUTH_TOKEN_KEY`).

Both reuse the same underlying OAuth *client* configuration (client
id/secret/secrets file — extracted into
`infrastructure/gmail/oauth_client.py::load_google_oauth_client_config` to
avoid duplicating that lookup), but each identity has its own consent screen,
its own refresh token, and its own on/off switch in Settings ("Authorize
Pub/Sub" / "Revoke Pub/Sub", independent of "Connect Gmail" / "Disconnect").
No service-account JSON key is used or read anywhere in this codebase; the
`.gitignore` additions (`service-account*.json`, `gcp-*.json`, etc.) are a
defensive guard against ever accidentally introducing one.

`MonitoringStatusDto` (what the UI reads) is verified by test
(`test_monitoring_status_dto_never_exposes_credentials`) to have no
token/credential/secret-shaped field, and no field value containing the
substring "token" — Settings shows *whether* Pub/Sub is authorized, never a
credential.

---

## 6. Monitored labels, not hardcoded topics

`monitored_labels.py::monitored_label_ids(uow)` derives the watched Gmail
label set from `Topic.source_configuration` for every **enabled**,
Gmail-backed Topic — the same label↔Topic mapping Settings already manages
via "Map selected label to topic". There is no hardcoded topic name (no
"TRUMP", no "Modi") anywhere in Phase 10 code; watch/history filtering is
entirely data-driven. Disabling a Topic or changing its label mapping is
reflected the next time the watch is (re-)established (initial start, manual
renewal, or 404-driven recovery) — the worker does not need to be
restarted, but no live in-flight watch is retroactively narrowed.

---

## 7. Watch lifecycle: start, renew, 404-recovery

`GmailWatchLifecycleService.establish_watch()` is the single method used for
**both** initial setup and any later re-baselining (manual renewal, or
404/history-unavailable recovery) — `users.watch` is idempotent: calling it
again simply resets the expiration and returns a fresh `historyId`. One
method safely serves all three callers.

`StartMonitoringUseCase.execute()` deliberately establishes the watch
*before* running the initial full sync:

1. `establish_watch()` — the stored `current_history_id` now covers "now."
2. `sync_all_monitored_topics()` — backfills anything already present using
   the exact Phase 9 "Save recent messages" path.
3. Start the background worker.

Any mailbox change that lands in the gap between steps 1 and 2 is safely
covered by step 2's full sync; anything landing after step 1 also triggers a
future Pub/Sub notification. The unavoidable overlap is harmless because of
Phase 9's idempotent dedup (§4) — this was a deliberate simplification versus
threading a precise "which messages happened before/after watch
registration" distinction through the API, which Gmail's Watch response does
not actually provide.

**404 / history-unavailable recovery:** `GmailHistoryProvider.list_history`
raises `GmailHistoryUnavailableError` on a 404 or "invalid/expired
startHistoryId" response (Gmail retains history for a limited window).
`GmailPubSubNotificationProcessor` catches this, runs
`GmailFullSyncService.sync_all_monitored_topics()` (bounded backfill, same
Phase 9 path), then calls `establish_watch()` again to obtain a fresh
history baseline — never crashes, never gets permanently stuck.

**Renewal:** Gmail watches expire after at most 7 days.
`GmailWatchLifecycleService.renew_if_needed(margin_hours)` is a cheap
DB-only read on every worker loop iteration (not a Gmail API call) and only
calls `establish_watch()` when the stored `watch_expiration` is within the
configured margin (default 24h, `INSIGHTFLOW_MONITORING_WATCH_RENEWAL_MARGIN_HOURS`).
A manual "Renew Watch" button is also available in Settings.

---

## 8. History-cursor safety

`GmailHistorySyncService._collect_candidates()` pages through
`history.list` results, deduplicates by `message_id`, and caps the batch at
`INSIGHTFLOW_MONITORING_HISTORY_BATCH_SIZE` (default 50) — each candidate
carries its own per-record `history_id`, not just the page's top-level one.
Cursor advancement is deliberately conservative:

- If the batch was **not** truncated (all available history was consumed),
  the cursor advances to the response's final `historyId`.
- If the batch **was** truncated by the size cap, the cursor advances only
  to the **last successfully processed candidate's own** `history_id` — never
  past unprocessed work, even though later candidates exist in a page
  already fetched. The remainder is picked up on the next Pub/Sub
  notification or worker cycle.

This is the single most safety-critical piece of Phase 10 and is covered
explicitly by `test_batch_limit_truncates_and_advances_cursor_safely`.

---

## 9. Concurrency, acknowledgement, and idempotency

- `GmailPubSubNotificationProcessor` holds one `threading.Lock` per process,
  serializing all history-sync work for the account — two Pub/Sub
  notifications arriving concurrently cannot interleave cursor updates.
- The worker (`GmailMonitoringWorker`) is a single background
  `threading.Thread(daemon=True)`, not a Qt `QThread` — the `application`
  layer cannot import PySide6 (enforced by
  `tests/architecture/test_dependency_rules.py`), so the worker uses stdlib
  threading with a `threading.Event` for cooperative stop and
  `thread.join(timeout=...)`. The Settings page's Start/Stop buttons run in
  their own `QThread` wrapper only to keep the *use-case call itself* off the
  Qt GUI thread; the actual monitoring loop lives entirely in the plain
  Python thread the use case starts.
- **Acknowledgement policy:** a Pub/Sub message is acknowledged **only**
  after `GmailPubSubNotificationProcessor.process()` returns `True` — i.e.
  history sync (or full-sync recovery) completed without an unexpected
  exception. A malformed/unparseable notification payload is acknowledged
  immediately (poison-message safety: it can never succeed, so redelivering
  it forever would be pure noise). A transient processing failure (anything
  other than the handled 404 case) is **not** acknowledged — Pub/Sub
  redelivers it, and since dedup makes re-processing safe, no message is
  ever silently dropped.
- **Idempotency / duplicate notifications:** Pub/Sub is at-least-once
  delivery. A duplicate or redundant notification re-runs history sync from
  the already-advanced cursor; if nothing new is found, zero events are
  created. If the same message is somehow re-processed, Phase 9's
  `source_id + external_id` uniqueness rejects it as a duplicate, not an
  error. Verified end-to-end in
  `tests/integration/test_gmail_realtime_monitoring.py::test_duplicate_notification_does_not_duplicate_event`.
- **Restart recovery:** the durable `monitoring_state.current_history_id`
  cursor (SQLite, survives process restart) is what a notification is
  synced from — not any in-memory state — so a notification that arrives
  after a restart, or one whose processing never completed before shutdown,
  resumes correctly from the last durably-recorded cursor position. Verified
  in `test_recovery_after_restart_processes_pending_work`.
- Gmail disconnect stops active monitoring
  (`DisconnectGmailUseCase` now also stops the worker via a structural
  `MonitoringWorkerHandle` Protocol, avoiding a circular import — see §12.2);
  reconnecting does not auto-restart monitoring, the user must click Start
  Monitoring again (an explicit action, matching the spec).

---

## 10. Settings & Dashboard UI

Settings gained a "Real-time monitoring" section: status line (status,
account, watched topics, Pub/Sub project/topic/subscription, watch
expiration, last sync, last notification, last error — **never** a
credential), plus Authorize/Revoke Pub/Sub, Start/Stop Monitoring, and Renew
Watch buttons. Button enablement rules mirror the real preconditions (Start
requires Gmail connected + Pub/Sub authorized + not already running; Stop/
Renew require monitoring to actually be running; Revoke Pub/Sub is disabled
while monitoring is active).

The Dashboard's monitoring status line now reflects
`monitoring_state.status` for the connected account instead of a static
placeholder — it shows "Not configured" until Gmail is connected *and*
monitoring has actually been started, and never shows "RUNNING" before the
pipeline is verifiably active (verified by
`test_dashboard_does_not_show_running_until_monitoring_actually_started`).

---

## 11. Explicitly NOT implemented in Phase 10

Per the phase boundary: AI analysis, Windows toast/desktop notifications,
attachment downloading, priority engine, story grouping, script/video
generation, YouTube upload, or any change to how Topics/Dashboard/
Intelligence views render beyond the monitoring status line above. No Gmail
*polling* exists anywhere — the only Gmail API calls the worker makes are the
already-covered watch renewal check (a local DB read, not an API call unless
renewal is actually due) and history/message calls triggered by an actual
Pub/Sub notification.

---

## 12. Design decisions worth a second look

1. **Watch-before-full-sync overlap (§7).** Accepted as harmless due to
   idempotent dedup rather than building precise before/after history
   sequencing — simpler, but means the very first full sync after Start
   could occasionally re-fetch a message Gmail's Watch technically already
   covered (caught as a duplicate, not wasted user-visible work, just one
   extra `messages.get` call).
2. **Circular import resolved via a local structural `Protocol`.**
   `commands/gmail.py` (`DisconnectGmailUseCase`) needs to stop the
   monitoring worker but cannot import the concrete `MonitoringWorkerHandle`
   without a cycle (`services/monitoring_worker_handle.py` →
   `gmail_monitoring_worker.py` → `gmail_pubsub_processor.py` →
   `gmail_full_sync.py` → back to `commands/gmail.py` for
   `IngestTopicMessagesUseCase`). Resolved with a local
   `@runtime_checkable Protocol` requiring only `is_running` / `stop()`
   rather than restructuring the service dependency graph. Acceptable, but a
   future refactor could invert the dependency (e.g. an event/callback
   registered by bootstrap) if more such cycles appear.
3. **Renewal margin default (24h) and full-sync/batch-size defaults (50)**
   are reasonable guesses, not requirements from any doc — all are
   `INSIGHTFLOW_MONITORING_*` env-configurable without a code change if a
   real account's mail volume needs different bounds.
4. **`GmailMonitoringWorker` polls Pub/Sub on a fixed idle interval**
   (`INSIGHTFLOW_MONITORING_IDLE_POLL_SECONDS`, default 5s) rather than a
   long-lived streaming pull — the REST `projects.subscriptions.pull` API
   (chosen to avoid adding the heavier `google-cloud-pubsub` gRPC dependency)
   does not offer server-side streaming; this is standard practice for the
   REST Pub/Sub API and is explicitly *not* Gmail polling (no Gmail API call
   happens on an idle empty pull).

---

## 13. Testing

- **Domain:** `tests/unit/domain/test_monitoring_state.py` — status
  transitions, `watch_needs_renewal` margin logic.
- **Application:** `test_gmail_history_sync.py`, `test_gmail_full_sync.py`,
  `test_gmail_watch_lifecycle.py`, `test_gmail_pubsub_processor.py`,
  `test_gmail_monitoring_worker.py`, `test_monitoring_commands.py` — label
  filtering, pagination, truncated-batch cursor safety, duplicate/malformed
  message resilience, 404 recovery, concurrent-notification serialization,
  ack-only-on-success, poison-message handling, non-blocking worker start,
  credential-free `MonitoringStatusDto`.
- **Infrastructure:** `test_gmail_monitoring_adapter.py` (watch/history
  request+response mapping, 404 translation, `messagesAdded`/`labelsAdded`
  extraction), `test_pubsub_adapter.py` (pull/ack REST mapping, base64
  decoding, error translation), `test_pubsub_message_parser.py` (never
  raises, coerces `historyId`, ignores unexpected fields).
- **Database:** `tests/integration/test_migrations.py` (migration 002
  applies, `monitoring_state` table present),
  `tests/integration/test_repositories.py::test_monitoring_state_crud_and_round_trip`
  (real `SQLiteUnitOfWork` round-trip, including `update()` on a missing row
  raising `PersistenceError`).
- **Integration (end-to-end):**
  `tests/integration/test_gmail_realtime_monitoring.py` — full
  notification → history → ingestion → `IntelligenceEvent` pipeline through
  a real `GmailMonitoringWorker` pull/process/ack loop against fakes;
  duplicate-notification idempotency; restart recovery (fresh
  `ApplicationUseCases` against the same durable store); 404 → full-sync
  recovery with monitoring remaining `RUNNING` afterward; multi-notification
  sequential cursor advancement.
- **UI:** `tests/unit/presentation/test_monitoring_ui.py` — Settings button
  enablement across every precondition combination, Start/Stop/Renew flows,
  no-credential-leak assertion on the rendered status text, and the
  Dashboard "never shows RUNNING before monitoring is actually active"
  requirement.
- **Quality gates:** `pytest` (303 passed), `ruff check src tests` (clean),
  `mypy` (clean, 220 source files), `python -m insightflow` GUI smoke test
  (exit 0, migrations `[1, 2]` applied, clean shutdown). `ruff format --check`
  reports a pre-existing, repo-wide CRLF/LF line-ending mismatch (present on
  the pre-Phase-10 codebase too — verified via `git stash`) unrelated to
  Phase 10; every file Phase 10 added or touched was individually confirmed
  clean with `ruff format` and is not the source of that mismatch.

### Manual testing (real Gmail account)

Automated tests use `FakeGmailAdapter`/`FakePubSubSubscriber` exclusively —
no code in this phase has been exercised against a real Gmail inbox or a
real Google Cloud project. Before relying on this in production, perform:

1. **Google Cloud setup** (one-time, per Google account):
   a. Create/select a Google Cloud project.
   b. Enable the **Gmail API** and **Cloud Pub/Sub API**.
   c. Create a Pub/Sub topic (e.g. `gmail-notify`).
   d. Grant `gmail-api-push@system.gserviceaccount.com` the
      **Pub/Sub Publisher** role on that topic (Gmail's own publishing
      identity — required by `users.watch`, documented by Google; this is
      *not* the desktop app's identity).
   e. Create a **pull** subscription on that topic (e.g. `gmail-notify-sub`).
   f. Ensure your OAuth client (already configured for Gmail per Phase 6/8)
      is a **Desktop app** type client — the same client is reused for the
      Pub/Sub consent.
   g. Set in `.env`: `INSIGHTFLOW_GMAIL_PUBSUB_PROJECT_ID`,
      `INSIGHTFLOW_GMAIL_PUBSUB_TOPIC=gmail-notify`,
      `INSIGHTFLOW_GMAIL_PUBSUB_SUBSCRIPTION=gmail-notify-sub`.
2. Launch InsightFlow, connect Gmail, map at least one label to a Topic.
3. Click **Authorize Pub/Sub** — a second browser consent screen appears
   (scope: `.../auth/pubsub`).
4. Click **Start Monitoring** — status should move to `RUNNING`, watch
   expiration populated (~7 days out).
5. Send/receive a real email matching the monitored label from another
   account.
6. Within `INSIGHTFLOW_MONITORING_IDLE_POLL_SECONDS` (default 5s), the
   message should appear in the Topic's events (Intelligence/Dashboard)
   without any manual action.
7. Click **Renew Watch** and confirm the expiration timestamp updates.
8. Click **Stop Monitoring**, confirm status returns to `STOPPED` and no
   further messages are ingested until Start is clicked again.
9. Do **not** delete the existing TRUMP Topic/label mapping used by earlier
   phases' manual tests — Phase 10 reuses it rather than requiring a new one.

This manual pass has **not** been performed as part of this implementation
(no live Google Cloud project/Gmail account is available in this
environment) and should be run by the account owner before considering
Phase 10 production-ready.

---

## 14. Deferred to later phases

- AI summarization/analysis, priority engine, notification policy, desktop
  toast popups.
- Attachment downloading.
- Story grouping.
- Any script/video generation or YouTube upload.
- Multi-account monitoring (the schema and repository already support
  multiple `(account_id, provider)` rows; only single-account UI/use-case
  flows exist today).
- Precise "before/after watch registration" history sequencing (§12.1).
