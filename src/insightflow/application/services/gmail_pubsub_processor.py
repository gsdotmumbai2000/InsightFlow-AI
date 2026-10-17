"""Orchestrates one Gmail Pub/Sub notification into a history sync (Phase 10).

Processing algorithm (see docs/17_Phase10_Gmail_Realtime_Monitoring_Notes.md):

    Pub/Sub notification
        -> identify Gmail account
        -> load monitoring state
        -> acquire per-account synchronization lock
        -> compare history IDs
        -> history.list(startHistoryId)
        -> collect messagesAdded / relevant labelsAdded
        -> filter by monitored labels/topics
        -> retrieve full Gmail messages
        -> EmailMessageDto
        -> existing Phase 9 ingestion
        -> created / duplicate / failed
        -> update monitoring history state
        -> caller acknowledges Pub/Sub notification

History-unavailable (404) recovery falls back to a full synchronization
followed by re-establishing the watch to obtain a fresh history baseline.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope
from insightflow.application.dto.monitoring import PubSubNotificationDto
from insightflow.application.exceptions.gmail import GmailHistoryUnavailableError
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.gmail_full_sync import GmailFullSyncService
from insightflow.application.services.gmail_history_sync import (
    GmailHistorySyncService,
)
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)
from insightflow.application.services.monitoring_events import (
    MonitoringEventCallback,
)
from insightflow.domain import SourceType

logger = logging.getLogger("insightflow.application.monitoring")


def _noop_event(reason: str) -> None:
    del reason


class GmailPubSubNotificationProcessor:
    """Serializes mailbox synchronization for one Gmail account.

    A single internal lock ensures overlapping Pub/Sub notifications for
    the same account never interleave history processing (which could
    corrupt the stored cursor); unrelated application work is unaffected
    and the GUI thread is never involved here.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        history_sync: GmailHistorySyncService,
        full_sync: GmailFullSyncService,
        watch_lifecycle: GmailWatchLifecycleService,
        on_event: MonitoringEventCallback = _noop_event,
    ) -> None:
        self._uow_factory = uow_factory
        self._history_sync = history_sync
        self._full_sync = full_sync
        self._watch_lifecycle = watch_lifecycle
        self._on_event = on_event
        self._lock = threading.Lock()

    def process(self, notification: PubSubNotificationDto) -> bool:
        """Process one notification. Returns True only if safe to acknowledge."""
        with self._lock:
            result = self._process_locked(notification)
        # Fired outside the lock — one refresh notification per processed
        # Pub/Sub message, covering the notification/sync/error/status
        # changes _process_locked may have made to MonitoringState.
        self._on_event("notification_processed")
        return result

    def _process_locked(self, notification: PubSubNotificationDto) -> bool:
        account_id = notification.email_address
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
        if state is None or state.current_history_id is None:
            logger.warning(
                "Gmail notification with no synchronization cursor; "
                "running full sync account_id=%s",
                account_id,
            )
            return self._recover_with_full_sync(account_id)

        self._record_notification(account_id)
        try:
            outcome = self._history_sync.sync(
                account_id=account_id, start_history_id=state.current_history_id
            )
        except GmailHistoryUnavailableError:
            logger.warning(
                "Gmail history unavailable (404) account_id=%s; full sync",
                account_id,
            )
            return self._recover_with_full_sync(account_id)
        except Exception as exc:
            logger.warning(
                "Gmail history sync failed account_id=%s error=%s",
                account_id,
                type(exc).__name__,
            )
            self._mark_error(account_id, str(exc))
            return False

        if outcome.new_history_id is not None:
            self._advance_history(account_id, outcome.new_history_id)
        logger.info(
            "Gmail history sync completed account_id=%s processed=%s created=%s "
            "duplicate=%s failed=%s has_more=%s",
            account_id,
            outcome.processed_message_count,
            outcome.created_count,
            outcome.duplicate_count,
            outcome.failed_count,
            outcome.has_more,
        )
        return True

    def _recover_with_full_sync(self, account_id: str) -> bool:
        try:
            self._full_sync.sync_all_monitored_topics()
            self._watch_lifecycle.establish_watch(account_id=account_id)
        except Exception as exc:
            logger.warning(
                "Gmail full-sync recovery failed account_id=%s error=%s",
                account_id,
                type(exc).__name__,
            )
            self._mark_error(account_id, str(exc))
            return False
        return True

    def _record_notification(self, account_id: str) -> None:
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.record_notification()
            uow.monitoring_states.update(state)
            uow.commit()

    def _advance_history(self, account_id: str, history_id: str) -> None:
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.advance_history(history_id)
            state.mark_running()
            uow.monitoring_states.update(state)
            uow.commit()

    def _mark_error(self, account_id: str, message: str) -> None:
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.mark_error(message)
            uow.monitoring_states.update(state)
            uow.commit()

    def record_worker_error(self, account_id: str, message: str) -> None:
        """Record a transient worker-level failure (e.g. a failed Pub/Sub
        pull or acknowledge) without changing the lifecycle status.

        Called by ``GmailMonitoringWorker`` directly — distinct from
        ``_mark_error``, which represents an actual processing failure for
        one notification and transitions status to ``ERROR``. A single
        failed pull/ack is expected to be transient and must not stop the
        worker or make a healthy ``RUNNING`` worker look broken; it only
        needs to be visible in ``last_error`` for observability. ``message``
        must never contain email content or credentials — callers pass a
        short, generic description (e.g. an exception type name).
        """
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.record_error(message)
            uow.monitoring_states.update(state)
            uow.commit()
        self._on_event("monitoring_error")
