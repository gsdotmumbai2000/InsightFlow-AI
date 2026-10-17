"""Automatic AI-analysis dispatch on newly created IntelligenceEvents.

Wired as the ``on_event_created`` callback into ``IngestTopicMessagesUseCase``
so *every* ingestion path (Pub/Sub history sync, full sync, manual "Save
recent messages") gets automatic AI dispatch generically, without any of
them knowing AI exists. Dispatch must never raise: a disabled profile, an
unconfigured topic, or a full queue must never break Gmail ingestion.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope
from insightflow.application.commands.ai_settings import ai_analysis_enabled
from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    EventId,
    EventProcessingStatus,
    IntelligenceEvent,
    IntelligenceEventCreated,
)
from insightflow.domain.exceptions import InvalidStateTransitionError

logger = logging.getLogger("insightflow.application.ai")

EnqueueAIJob = Callable[[AIAnalysisJob], None]

DEFAULT_PENDING_SCAN_LIMIT = 50


def begin_ai_processing(uow: UnitOfWork, event: IntelligenceEvent) -> None:
    """Transition an event into AI_PROCESSING and persist it.

    Shared by automatic dispatch and manual reprocessing so both paths
    show the same "AI analysis in progress..." state.
    """
    event.mark_processing()
    uow.events.update(event)
    uow.commit()


def find_pending_ai_jobs(
    uow_factory: Callable[[], UnitOfWork],
    *,
    limit: int = DEFAULT_PENDING_SCAN_LIMIT,
) -> list[AIAnalysisJob]:
    """Jobs for every event persisted as AI_PROCESSING.

    The database is the hand-off point between processes (Phase 13): the
    Desktop only marks an event AI_PROCESSING, and the Agent's ``AIWorker``
    picks it up from here. Also recovers jobs whose in-memory queue entry
    was lost when a previous Agent exited mid-queue.
    """
    with unit_of_work_scope(uow_factory) as uow:
        events = uow.events.list_by_status(
            EventProcessingStatus.AI_PROCESSING, limit=limit
        )
    # manual=True: turning automatic analysis off cancels everything waiting
    # and stops new automatic dispatch, so while it is off anything persisted
    # as AI_PROCESSING came from an explicit Analyze click.
    return [AIAnalysisJob(event_id=event.id.value, manual=True) for event in events]


def ai_job_should_run(
    uow_factory: Callable[[], UnitOfWork], job: AIAnalysisJob
) -> bool:
    """Checked by the AI worker right before each (billed) AI call.

    False when the event is gone or no longer waiting (e.g. cancelled by
    turning automatic analysis off), or when the job is automatic and
    automatic analysis is now off — in which case its event is cancelled
    too, so it is not picked up again later.
    """
    with unit_of_work_scope(uow_factory) as uow:
        event = uow.events.get(EventId(job.event_id))
        if event is None or event.status is not EventProcessingStatus.AI_PROCESSING:
            return False
        if job.manual or ai_analysis_enabled(uow):
            return True
        event.cancel_ai_processing()
        uow.events.update(event)
        uow.commit()
        return False


def mark_ai_job_failed(
    uow_factory: Callable[[], UnitOfWork], job: AIAnalysisJob
) -> None:
    """Move a job's event out of AI_PROCESSING after the job raised.

    Without this, a job that can never succeed (e.g. its topic has no AI
    profile) would stay AI_PROCESSING and be re-found by every pending scan.
    """
    with unit_of_work_scope(uow_factory) as uow:
        event = uow.events.get(EventId(job.event_id))
        if event is None or event.status is not EventProcessingStatus.AI_PROCESSING:
            return
        event.mark_failed()
        uow.events.update(event)
        uow.commit()


class AIAnalysisDispatcher:
    """Decides whether a newly created event should be analyzed, and enqueues it."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        enqueue: EnqueueAIJob,
        *,
        enabled: bool,
    ) -> None:
        self._uow_factory = uow_factory
        self._enqueue = enqueue
        self._enabled = enabled

    def dispatch(self, event: IntelligenceEventCreated) -> None:
        """Never raises — logged and swallowed on any failure."""
        try:
            self._dispatch(event)
        except Exception:
            logger.warning(
                "AI dispatch failed event_id=%s",
                event.event_id.value,
                exc_info=True,
            )

    def _dispatch(self, event: IntelligenceEventCreated) -> None:
        if not self._enabled:
            return
        if event.topic_id is None:
            return
        with unit_of_work_scope(self._uow_factory) as uow:
            if not ai_analysis_enabled(uow):
                return  # turned off in Settings: the event stays RECEIVED
            intelligence_event = uow.events.get(event.event_id)
            if intelligence_event is None:
                return
            topic = uow.topics.get(event.topic_id)
            if topic is None or topic.ai_profile_id is None:
                return
            profile = uow.profiles.get(topic.ai_profile_id)
            if profile is None or not profile.enabled:
                return
            try:
                begin_ai_processing(uow, intelligence_event)
            except InvalidStateTransitionError:
                logger.debug(
                    "Skipping AI dispatch (already processing) event_id=%s",
                    intelligence_event.id.value,
                )
                return
        self._enqueue(AIAnalysisJob(event_id=intelligence_event.id.value))
