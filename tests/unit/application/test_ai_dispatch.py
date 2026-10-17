"""AIAnalysisDispatcher tests (Phase 11).

Dispatch must never raise (it runs inline in the Gmail ingestion path) and
must only enqueue when AI is enabled, the topic has a configured/enabled
profile, and the event exists.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.services.ai_dispatch import AIAnalysisDispatcher
from insightflow.domain import (
    AIProfile,
    EventId,
    IntelligenceEvent,
    IntelligenceEventCreated,
    SourceConfiguration,
    SourceReference,
    SourceType,
    Topic,
    TopicId,
)


def _topic_with_profile(store: InMemoryStore, *, profile_enabled: bool = True) -> Topic:
    profile = AIProfile.create(
        name="Default",
        instructions="Summarize",
        output_schema_version="v1",
        enabled=profile_enabled,
    )
    topic = Topic.create(
        name="Topic",
        source_configuration=SourceConfiguration(
            source_type=SourceType.GENERIC,
            source_id="src",
            source_identifier="ident-1",
        ),
        ai_profile_id=profile.id,
    )
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.topics.add(topic)
        uow.commit()
    return topic


def _topic_without_profile(store: InMemoryStore) -> Topic:
    topic = Topic.create(
        name="NoProfile",
        source_configuration=SourceConfiguration(
            source_type=SourceType.GENERIC,
            source_id="src",
            source_identifier="ident-2",
        ),
    )
    with store.unit_of_work_factory() as uow:
        uow.topics.add(topic)
        uow.commit()
    return topic


def _create_event(store: InMemoryStore, *, topic_id: str) -> IntelligenceEventCreated:
    event = IntelligenceEvent.create(
        source=SourceReference(
            source_type=SourceType.GENERIC, source_id="src", external_id="ext-1"
        ),
        topic_id=None,
    )
    event.topic_id = TopicId(topic_id)
    with store.unit_of_work_factory() as uow:
        uow.events.add(event)
        uow.commit()
    return IntelligenceEventCreated(
        event_id=event.id,
        topic_id=TopicId(topic_id),
        occurred_at=datetime.now(UTC),
    )


def test_dispatch_enqueues_and_marks_processing_when_configured() -> None:
    store = InMemoryStore()
    topic = _topic_with_profile(store)
    domain_event = _create_event(store, topic_id=topic.id.value)
    jobs: list[AIAnalysisJob] = []
    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, jobs.append, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert jobs == [AIAnalysisJob(event_id=domain_event.event_id.value)]
    with store.unit_of_work_factory() as uow:
        stored_event = uow.events.get(EventId(domain_event.event_id.value))
    assert stored_event is not None
    assert stored_event.status.value == "AI_PROCESSING"


def test_dispatch_skips_when_disabled() -> None:
    store = InMemoryStore()
    topic = _topic_with_profile(store)
    domain_event = _create_event(store, topic_id=topic.id.value)
    jobs: list[AIAnalysisJob] = []
    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, jobs.append, enabled=False
    )

    dispatcher.dispatch(domain_event)

    assert jobs == []


def test_dispatch_skips_when_topic_has_no_profile() -> None:
    store = InMemoryStore()
    topic = _topic_without_profile(store)
    domain_event = _create_event(store, topic_id=topic.id.value)
    jobs: list[AIAnalysisJob] = []
    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, jobs.append, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert jobs == []


def test_dispatch_skips_when_profile_disabled() -> None:
    store = InMemoryStore()
    topic = _topic_with_profile(store, profile_enabled=False)
    domain_event = _create_event(store, topic_id=topic.id.value)
    jobs: list[AIAnalysisJob] = []
    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, jobs.append, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert jobs == []


def test_dispatch_never_raises_on_internal_error() -> None:
    store = InMemoryStore()
    topic = _topic_with_profile(store)
    domain_event = _create_event(store, topic_id=topic.id.value)

    def _broken_enqueue(job: AIAnalysisJob) -> None:
        raise RuntimeError("boom")

    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, _broken_enqueue, enabled=True
    )

    dispatcher.dispatch(domain_event)  # must not raise
