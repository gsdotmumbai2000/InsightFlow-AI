"""Bounded full synchronization across all monitored Gmail Topics (Phase 10).

Used for initial monitoring setup and Gmail history-unavailable (404)
recovery. Does not implement a second ingestion path — reuses
``IngestTopicMessagesUseCase.execute()`` per monitored Topic exactly as the
manual "Save recent messages" action does (FullSync -> RetrieveTopicMessages
-> IngestTopicMessages).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from insightflow.application._support import unit_of_work_scope
from insightflow.application.commands.gmail import IngestTopicMessagesUseCase
from insightflow.application.dto.email import IngestTopicMessagesRequest
from insightflow.application.exceptions import ApplicationError
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import IntelligenceEventCreated, SourceType

logger = logging.getLogger("insightflow.application.monitoring")

DEFAULT_FULL_SYNC_MAX_MESSAGES = 50


@dataclass(frozen=True, slots=True)
class FullSyncOutcome:
    topic_count: int = 0
    created_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)


class GmailFullSyncService:
    """Bounded backfill for every enabled Gmail-mapped Topic."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        ingest: IngestTopicMessagesUseCase,
        *,
        max_messages_per_topic: int = DEFAULT_FULL_SYNC_MAX_MESSAGES,
        on_event_created: Callable[[IntelligenceEventCreated], None] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._ingest = ingest
        self._max_messages_per_topic = max(1, max_messages_per_topic)
        self._on_event_created = on_event_created

    def sync_all_monitored_topics(self) -> FullSyncOutcome:
        with unit_of_work_scope(self._uow_factory) as uow:
            topics = [
                topic
                for topic in uow.topics.list_enabled()
                if topic.source_configuration.source_type is SourceType.GMAIL
            ]

        created = duplicate = failed = 0
        errors: list[str] = []
        for topic in topics:
            try:
                result = self._ingest.execute(
                    IngestTopicMessagesRequest(
                        topic_id=topic.id.value,
                        max_messages=self._max_messages_per_topic,
                    )
                )
            except ApplicationError as exc:
                logger.warning(
                    "Full sync failed topic_id=%s error=%s",
                    topic.id.value,
                    type(exc).__name__,
                )
                errors.append(f"{topic.name}: {exc}")
                continue
            created += len(result.created)
            duplicate += result.duplicate_count
            failed += len(result.failed)
            if self._on_event_created is not None:
                for domain_event in result.domain_events:
                    self._on_event_created(domain_event)

        logger.info(
            "Full sync completed topics=%s created=%s duplicate=%s failed=%s",
            len(topics),
            created,
            duplicate,
            failed,
        )
        return FullSyncOutcome(
            topic_count=len(topics),
            created_count=created,
            duplicate_count=duplicate,
            failed_count=failed,
            errors=tuple(errors),
        )
