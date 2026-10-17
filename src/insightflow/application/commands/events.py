"""Intelligence event use cases."""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.mappers import event_to_dto
from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    IntelligenceEventDto,
)
from insightflow.application.exceptions import (
    ApplicationValidationError,
    DuplicateEventError,
    EventNotFoundError,
    TopicNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    ContentHash,
    EventId,
    IntelligenceEvent,
    Priority,
    SourceReference,
    SourceType,
    TopicId,
)


class CreateIntelligenceEventUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: CreateIntelligenceEventRequest) -> IntelligenceEventDto:
        with use_case_scope("CreateIntelligenceEvent"):

            def _run() -> IntelligenceEventDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    source = SourceReference(
                        source_type=SourceType(request.source_type),
                        source_id=request.source_id,
                        external_id=request.external_id,
                        thread_id=request.thread_id,
                        account_id=request.account_id,
                        url=request.url,
                    )
                    existing = uow.events.find_by_external_id(
                        source_id=source.source_id,
                        external_id=source.external_id,
                    )
                    if existing is not None:
                        raise DuplicateEventError(
                            "An event already exists for this source identity."
                        )
                    # Cleared by the user: never re-ingest it (full sync
                    # re-reads recent messages on every Agent start).
                    if uow.events.was_cleared(
                        source_id=source.source_id, external_id=source.external_id
                    ):
                        raise DuplicateEventError(
                            "This message was cleared and is not ingested again."
                        )
                    topic_id = None
                    if request.topic_id is not None:
                        topic_id = TopicId(request.topic_id)
                        if uow.topics.get(topic_id) is None:
                            raise TopicNotFoundError(
                                f"Topic not found: {request.topic_id}"
                            )
                    priority = Priority(request.priority) if request.priority else None
                    content_hash = (
                        ContentHash(request.content_hash)
                        if request.content_hash
                        else None
                    )
                    event = IntelligenceEvent.create(
                        source=source,
                        topic_id=topic_id,
                        title=request.title,
                        normalized_content=request.normalized_content,
                        source_published_at=request.source_published_at,
                        received_at=request.received_at,
                        priority=priority,
                        content_hash=content_hash,
                    )
                    uow.events.add(event)
                    uow.commit()
                    return event_to_dto(event)

            return run_mutating(_run)


class ClearAllIntelligenceEventsUseCase:
    """Delete every intelligence event with its analyses and notifications.

    Cleared messages are remembered and never ingested again (see
    ``IntelligenceEventRepository.delete_all``). Returns how many events
    were deleted.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self) -> int:
        with use_case_scope("ClearAllIntelligenceEvents"):

            def _run() -> int:
                with unit_of_work_scope(self._uow_factory) as uow:
                    deleted = uow.events.delete_all()
                    uow.commit()
                    return deleted

            return run_mutating(_run)


class GetIntelligenceEventUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> IntelligenceEventDto:
        with (
            use_case_scope("GetIntelligenceEvent"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            event = uow.events.get(EventId(event_id))
            if event is None:
                raise EventNotFoundError(f"Event not found: {event_id}")
            return event_to_dto(event)


class ListRecentIntelligenceEventsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, *, limit: int = 50) -> list[IntelligenceEventDto]:
        with (
            use_case_scope("ListRecentIntelligenceEvents"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            events = uow.events.list_recent(limit=_positive_limit(limit))
            return [event_to_dto(event) for event in events]


class ListEventsByTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str, *, limit: int = 50) -> list[IntelligenceEventDto]:
        with (
            use_case_scope("ListEventsByTopic"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            if uow.topics.get(TopicId(topic_id)) is None:
                raise TopicNotFoundError(f"Topic not found: {topic_id}")
            events = uow.events.list_by_topic(
                TopicId(topic_id), limit=_positive_limit(limit)
            )
            return [event_to_dto(event) for event in events]


class MarkEventProcessingUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> IntelligenceEventDto:
        return _transition_event(self._uow_factory, event_id, "processing")


class MarkEventCompletedUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> IntelligenceEventDto:
        return _transition_event(self._uow_factory, event_id, "completed")


class MarkEventFailedUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> IntelligenceEventDto:
        return _transition_event(self._uow_factory, event_id, "failed")


class MarkEventIgnoredUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> IntelligenceEventDto:
        return _transition_event(self._uow_factory, event_id, "ignored")


def _positive_limit(limit: int) -> int:
    if limit < 1:
        raise ApplicationValidationError("limit must be >= 1")
    return limit


def _transition_event(
    uow_factory: Callable[[], UnitOfWork],
    event_id: str,
    action: str,
) -> IntelligenceEventDto:
    with use_case_scope(f"MarkEvent{action.title()}"):

        def _run() -> IntelligenceEventDto:
            with unit_of_work_scope(uow_factory) as uow:
                event = uow.events.get(EventId(event_id))
                if event is None:
                    raise EventNotFoundError(f"Event not found: {event_id}")
                if action == "processing":
                    event.mark_processing()
                elif action == "completed":
                    event.mark_completed()
                elif action == "failed":
                    event.mark_failed()
                elif action == "ignored":
                    event.mark_ignored()
                else:
                    raise ApplicationValidationError(f"Unknown event action: {action}")
                uow.events.update(event)
                uow.commit()
                return event_to_dto(event)

        return run_mutating(_run)
