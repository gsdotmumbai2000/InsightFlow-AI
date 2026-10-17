"""Windows-toast notification dispatch on newly created IntelligenceEvents.

Wired as an ``on_event_created`` callback into the real-time monitoring
services only (``GmailHistorySyncService``, ``GmailFullSyncService``) —
*not* into the generic ``IngestTopicMessagesUseCase`` hook Phase 11 uses
for AI dispatch. This is deliberate: a new real-time Gmail event should
notify, but a manual "Save recent messages" click should not, even though
both ultimately create an ``IntelligenceEvent`` through the same Phase 9
ingestion boundary. Reusing the exact ``IntelligenceEventCreated`` domain
event Phase 11 already returns (previously discarded by both services)
means no second Gmail-message deduplication system was introduced.

Dispatch must never raise: a disabled setting, a missing topic, or a
Windows-toast delivery failure must never break Gmail ingestion, AI
dispatch, or the monitoring worker.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope
from insightflow.application.ports.notifications import (
    NotificationPort,
    ToastNotificationRequest,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import IntelligenceEventCreated, Notification, Priority

logger = logging.getLogger("insightflow.application.notifications")

_FALLBACK_SUBJECT = "New email received"
_FALLBACK_APP_TITLE = "InsightFlow AI"
_MAX_SUBJECT_LENGTH = 200
_MAX_TOPIC_NAME_LENGTH = 100


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class ToastNotificationDispatcher:
    """Persists a ``Notification`` and requests a Windows toast for it."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        notification_port: NotificationPort,
        *,
        enabled: bool,
    ) -> None:
        self._uow_factory = uow_factory
        self._notification_port = notification_port
        self._enabled = enabled

    def dispatch(self, event: IntelligenceEventCreated) -> None:
        """Never raises — logged and swallowed on any failure."""
        try:
            self._dispatch(event)
        except Exception:
            logger.warning(
                "Windows toast notification failed event_id=%s",
                event.event_id.value,
                exc_info=True,
            )

    def _dispatch(self, event: IntelligenceEventCreated) -> None:
        if not self._enabled:
            return
        with unit_of_work_scope(self._uow_factory) as uow:
            intelligence_event = uow.events.get(event.event_id)
            if intelligence_event is None:
                return
            topic_name: str | None = None
            if event.topic_id is not None:
                topic = uow.topics.get(event.topic_id)
                topic_name = topic.name if topic is not None else None

            subject = _truncate(
                intelligence_event.title or _FALLBACK_SUBJECT, _MAX_SUBJECT_LENGTH
            )
            display_topic = (
                _truncate(topic_name, _MAX_TOPIC_NAME_LENGTH) if topic_name else None
            )
            notification = Notification.create(
                event_id=intelligence_event.id,
                topic_id=intelligence_event.topic_id,
                priority=intelligence_event.priority or Priority.MEDIUM,
                title=subject,
                summary=display_topic,
            )
            uow.notifications.add(notification)
            uow.commit()

        toast_title = (
            f"{_FALLBACK_APP_TITLE} — {display_topic}"
            if display_topic
            else _FALLBACK_APP_TITLE
        )
        logger.info(
            "Windows toast notification requested topic=%s event_id=%s",
            display_topic or "-",
            intelligence_event.id.value,
        )
        self._notification_port.notify(
            ToastNotificationRequest(
                title=toast_title,
                body=subject,
                event_id=intelligence_event.id.value,
            )
        )
