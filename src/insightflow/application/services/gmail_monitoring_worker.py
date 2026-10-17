"""Background Pub/Sub subscriber loop for real-time Gmail monitoring (Phase 10).

Runs on a plain ``threading.Thread`` daemon, never Qt — the application
layer must not import PySide6, and this keeps the pull/process/acknowledge
loop usable regardless of whether any UI window is open. A short, bounded
pull-then-idle loop against the Pub/Sub *subscription* drives processing;
this is polling Pub/Sub, not Gmail (``messages.list`` is never called here).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from insightflow.application.dto.monitoring import PubSubNotificationDto
from insightflow.application.ports.pubsub import PubSubSubscriber
from insightflow.application.services.gmail_pubsub_processor import (
    GmailPubSubNotificationProcessor,
)
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)

logger = logging.getLogger("insightflow.application.monitoring")

DEFAULT_PULL_MAX_MESSAGES = 10
DEFAULT_IDLE_POLL_SECONDS = 5.0
DEFAULT_WATCH_RENEWAL_MARGIN_HOURS = 24.0
DEFAULT_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class GmailMonitoringWorker:
    """Owns one background thread pulling/acking a Pub/Sub subscription.

    ``stop()`` is safe to call from any thread (including a Qt worker
    thread triggered by a "Stop Monitoring" button) and returns once the
    loop has exited or ``join_timeout_seconds`` elapses. The thread is
    also created as a daemon so it can never block process shutdown even
    if ``stop()`` is skipped.
    """

    def __init__(
        self,
        *,
        account_id: str,
        subscriber: PubSubSubscriber,
        processor: GmailPubSubNotificationProcessor,
        watch_lifecycle: GmailWatchLifecycleService,
        parse_notification: Callable[[bytes], PubSubNotificationDto | None],
        pull_max_messages: int = DEFAULT_PULL_MAX_MESSAGES,
        idle_poll_seconds: float = DEFAULT_IDLE_POLL_SECONDS,
        watch_renewal_margin_hours: float = DEFAULT_WATCH_RENEWAL_MARGIN_HOURS,
    ) -> None:
        self._account_id = account_id
        self._subscriber = subscriber
        self._processor = processor
        self._watch_lifecycle = watch_lifecycle
        self._parse_notification = parse_notification
        self._pull_max_messages = pull_max_messages
        self._idle_poll_seconds = idle_poll_seconds
        self._watch_renewal_margin_hours = watch_renewal_margin_hours
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"gmail-monitoring-{self._account_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("Gmail monitoring worker started account_id=%s", self._account_id)

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> bool:
        """Request the worker to stop.

        Signals ``stop_event`` immediately and unconditionally (never
        blocks). If ``join_timeout_seconds`` is a positive number, then
        additionally waits up to that many seconds for the background
        thread to actually exit. Pass ``0`` (or ``None``) for a
        non-blocking stop request — appropriate when calling from the Qt
        GUI thread (e.g. on window close), since the worker thread is a
        daemon and can never block process exit even if it is still
        inside a blocking Google API call when this returns.

        Returns ``True`` if the thread is confirmed stopped (or was never
        running), ``False`` if it is still alive when this returns —
        only possible when a blocking Google API call outlives
        ``join_timeout_seconds``.
        """
        self._stop_event.set()
        thread = self._thread
        if thread is not None and join_timeout_seconds:
            thread.join(timeout=join_timeout_seconds)
        still_alive = thread is not None and thread.is_alive()
        if not still_alive:
            self._thread = None
        logger.info(
            "Gmail monitoring worker stop requested account_id=%s stopped=%s",
            self._account_id,
            not still_alive,
        )
        return not still_alive

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._maybe_renew_watch()
            try:
                messages = self._subscriber.pull(max_messages=self._pull_max_messages)
            except Exception as exc:
                logger.warning(
                    "Gmail monitoring pull failed account_id=%s error=%s",
                    self._account_id,
                    type(exc).__name__,
                )
                self._record_worker_error(f"Pub/Sub pull failed: {type(exc).__name__}")
                self._stop_event.wait(self._idle_poll_seconds)
                continue

            if not messages:
                self._stop_event.wait(self._idle_poll_seconds)
                continue

            ack_ids: list[str] = []
            for message in messages:
                notification = self._safe_parse(message.data)
                if notification is None:
                    # Malformed payload can never be processed — ack it so
                    # it does not redeliver forever (poison-message safety).
                    ack_ids.append(message.ack_id)
                    continue
                if self._processor.process(notification):
                    ack_ids.append(message.ack_id)
                # else: leave unacknowledged; Pub/Sub will redeliver.
            if ack_ids:
                self._safe_acknowledge(tuple(ack_ids))

    def _safe_parse(self, data: bytes) -> PubSubNotificationDto | None:
        try:
            return self._parse_notification(data)
        except Exception as exc:
            logger.warning(
                "Malformed Gmail Pub/Sub notification account_id=%s error=%s",
                self._account_id,
                type(exc).__name__,
            )
            return None

    def _safe_acknowledge(self, ack_ids: tuple[str, ...]) -> None:
        try:
            self._subscriber.acknowledge(ack_ids)
        except Exception as exc:
            logger.warning(
                "Gmail monitoring acknowledge failed account_id=%s error=%s",
                self._account_id,
                type(exc).__name__,
            )
            self._record_worker_error(
                f"Pub/Sub acknowledge failed: {type(exc).__name__}"
            )

    def _record_worker_error(self, message: str) -> None:
        try:
            self._processor.record_worker_error(self._account_id, message)
        except Exception as exc:
            # Recording the error must never itself take down the loop.
            logger.warning(
                "Failed to record Gmail monitoring error account_id=%s error=%s",
                self._account_id,
                type(exc).__name__,
            )

    def _maybe_renew_watch(self) -> None:
        try:
            self._watch_lifecycle.renew_if_needed(
                account_id=self._account_id,
                margin_hours=self._watch_renewal_margin_hours,
            )
        except Exception as exc:
            logger.warning(
                "Gmail watch renewal check failed account_id=%s error=%s",
                self._account_id,
                type(exc).__name__,
            )
