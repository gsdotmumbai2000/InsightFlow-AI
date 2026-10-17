# Phase 12 — Windows Toast Notification System

## 1. Scope

Native Windows toast popups for newly created `IntelligenceEvent`s arriving
through the existing real-time Gmail → Pub/Sub pipeline. Only the delivery
mechanism is new; the `Notification` domain entity, repository, use cases,
DTOs, and Notifications page already existed (from earlier phases) and are
reused unchanged.

## 2. Architecture

```
Gmail Watch / Pub/Sub (Phase 10, unchanged)
      |
GmailPubSubNotificationProcessor.process()  (unchanged)
      |
GmailHistorySyncService.sync() / GmailFullSyncService.sync_all_monitored_topics()
      |  (on_event_created — NEW optional callback, only these two services)
      v
ToastNotificationDispatcher.dispatch()
      |
      +-- persists a Notification (existing entity/repository, PENDING status)
      |
      +-- NotificationPort.notify(ToastNotificationRequest)
                |
                v
    WindowsToastNotificationPort (infrastructure/notifications/windows_toast.py)
                |
                v
        windows_toasts.WindowsToaster.show_toast()
                |
                v
        Windows Action Center toast popup
```

`AIAnalysisDispatcher` (Phase 11) is wired separately, one layer lower, into
the generic `IngestTopicMessagesUseCase.on_event_created` hook — it still
fires for *every* ingestion path (real-time and manual). The toast
dispatcher is deliberately wired one layer higher, only into the two
services that are exclusively part of the real-time monitoring pipeline.
This is why a manual "Save recent messages" click creates an
`IntelligenceEvent` and (if configured) triggers AI analysis, but never a
toast — see §4.

## 3. Windows toast implementation

**Library: `windows_toasts` (>= 1.3).** Selected after inspecting
`pyproject.toml` (no notification library present) and verifying Python
3.13/Windows compatibility (pre-built `cp313-win_amd64` wheels for its
`winrt-*` dependencies installed cleanly). It wraps the native WinRT
`Windows.UI.Notifications` API with no `pywin32`/COM-registration
dependency, is actively maintained, and needs only the process name for
basic (non-interactible) toasts.

Declared as `windows-toasts>=1.3; sys_platform == 'win32'` in
`pyproject.toml` — it is not even installed on non-Windows platforms.

**Click activation is intentionally not implemented.** `windows_toasts`
offers `InteractableWindowsToaster` with an `on_activated` callback, but
its own documentation states this requires "a recognised AUMID" (e.g. a
registered Start Menu shortcut) — this desktop application does not set
one up, and without it, activation silently falls through to
`on_dismissed` with no usable payload. Rather than build a fragile
mechanism whose click behavior would be unreliable, the plain
`WindowsToaster` is used and clicking a toast simply dismisses it. This
is the one deliberately-not-implemented item from the spec (§11), by
design — "implement the notification first and document the activation
limitation rather than introducing a fragile mechanism."

## 4. Reuse, not reimplementation

- **`Notification` domain entity, `NotificationRepository`, and all four existing use cases** (`GetNotificationUseCase`, `ListRecentNotificationsUseCase`, `MarkNotificationDisplayedUseCase`, `MarkNotificationDismissedUseCase`) are used exactly as they already existed — no new notification concept was introduced.
- **The `notifications.provider` column already hardcoded `"windows"`** in `infrastructure/database/mappers.py` (`notification_to_row`) from earlier scaffolding — a strong signal this exact delivery mechanism was anticipated. No schema change, no migration.
- **The domain event that Phase 11 already returns but two services still discarded, finally gets consumed a second time.** `GmailHistorySyncService.sync()` and `GmailFullSyncService.sync_all_monitored_topics()` already had access to the `IntelligenceEventCreated` event (via `IngestMessageOutcome.domain_event` / `IngestTopicMessagesResult.domain_events`) but never used it for anything beyond what Phase 11's AI dispatcher consumes at a different layer. Both services gained one new optional constructor parameter, `on_event_created`, defaulting to `None` — fully backward compatible; every pre-existing call site and test is unaffected.
- **No second Gmail-message deduplication system.** Phase 9's `find_by_external_id` uniqueness check is the only place duplicate detection happens; a duplicate Pub/Sub delivery never produces a second `IntelligenceEventCreated`, so the toast dispatcher is never even invoked a second time for the same message.
- **The Notifications page is untouched.** It already renders whatever is in the `notifications` table; once `ToastNotificationDispatcher` starts persisting rows, they simply appear there via the existing `ListRecentNotificationsUseCase`/`NotificationsViewModel`/`NotificationsView` — no new UI screen, no changes to that page's code.

## 5. Trigger and duplicate handling

`ToastNotificationDispatcher.dispatch()` is called with an
`IntelligenceEventCreated` domain event exactly once per genuinely new
event, because:

- `IngestTopicMessagesUseCase.ingest_message()` only constructs that domain event on the `"CREATED"` branch — never on `"DUPLICATE"` — so a redelivered Pub/Sub notification for the same Gmail message never produces a second event.
- The dispatcher itself only ever persists one `Notification` row per call (add-only, matching `AIAnalysisRepository`'s existing append-only convention) and issues exactly one `NotificationPort.notify()` call per dispatch.
- Listing/loading already-persisted events (app startup, `ListRecentIntelligenceEventsUseCase`, `ListEventsByTopicUseCase`) never touches the dispatcher at all — only the ingestion methods construct and forward the domain event.

## 6. Configuration

`INSIGHTFLOW_NOTIFICATIONS_ENABLED` (default `true`) — a `NotificationsSettings.enabled` flag threaded through `build_use_cases` exactly like `AISettings`/`PubSubSettings`. When `false`, `ToastNotificationDispatcher.dispatch()` returns immediately (no `Notification` row, no toast, no exception) — Gmail monitoring, ingestion, and AI analysis are completely unaffected, since they are wired through entirely separate dispatchers.

## 7. Non-Windows behavior

`bootstrap/dependencies.py:build_notification_port()` checks
`platform.system()`. On Windows it lazily imports and returns
`WindowsToastNotificationPort`; on any other OS it returns
`UnsupportedNotificationPort` (a no-op that logs at DEBUG and never
raises) without ever importing `windows_toasts`/`winrt` — which, per
`pyproject.toml`'s `sys_platform == 'win32'` marker, are not even
installed there. `ToastNotificationDispatcher` and the rest of the
pipeline behave identically either way; only toast *delivery* differs.

## 8. Error handling and privacy

- `ToastNotificationDispatcher.dispatch()` wraps its entire body in one try/except — a disabled setting, a missing topic, a missing event, or a `NotificationPort.notify()` failure are all caught, logged as `"Windows toast notification failed"`, and never propagate. Gmail ingestion, AI dispatch, and the monitoring worker are unaffected by any of these.
- Logs contain only: event id, topic name, success/failure — never the email body, never credentials. The `Notification.title`/`summary` fields (subject/topic name) are the same non-secret display text already destined for the toast and the existing Notifications page; nothing more sensitive is logged.
- Subjects are capped at 200 characters, topic names at 100, both with a trailing `…` when truncated — bounded, safe display text only.

## 9. Explicitly NOT implemented (per spec)

Email polling, a second Gmail/Pub-Sub mechanism, another AI provider, AI prompt/model changes, story grouping, YouTube integration, attachment downloading, mobile/email/SMS/cloud notifications, notification scheduling, a separate notification-history system, and toast click-to-activate (documented limitation, §3).

## 10. Testing

- `tests/unit/application/test_notification_dispatch.py` — persistence + toast content, disabled setting, missing topic, empty/long subject truncation, delivery-failure isolation, priority defaults/passthrough, missing-event no-op.
- `tests/unit/infrastructure/test_windows_toast_adapter.py` — the internal `WindowsToaster` is replaced with a recording stub before `notify()` is ever called; **no real toast is displayed by the automated suite**.
- `tests/unit/application/test_gmail_history_sync.py` / `test_gmail_full_sync.py` — `on_event_created` fires once per new event, not for duplicates/resyncs.
- `tests/unit/application/test_gmail_ingestion.py` — manual `IngestTopicMessagesUseCase` (the "Save recent messages" path) never triggers a toast; listing existing events never triggers one either.
- `tests/integration/test_gmail_realtime_monitoring.py` — full fake Gmail/Pub-Sub pipeline: one new real-time event → exactly one toast with correct title/body; a duplicate Pub/Sub redelivery → no second toast; notifications disabled → event still created and monitoring stays `RUNNING`; AI enabled → AI analysis completes independently of the toast dispatch.
- `tests/architecture/test_dependency_rules.py` — `windows_toasts`/`winrt` may only be imported under `infrastructure/notifications/`.

## 11. Deferred / limitations

- Toast click-to-activate (see §3) — clicking dismisses rather than focusing the app.
- No notification-specific status indicator was added to the status bar (Diagnostics/main window) — out of scope per spec §18 ("no new large UI screen").
- The **real Windows manual test (§21 of the task) has not been performed** — it requires an actual Gmail message flowing through real-time monitoring while the app is open, observed visually on the user's machine. All automated coverage above uses fakes/stubs and never displays a real toast.
