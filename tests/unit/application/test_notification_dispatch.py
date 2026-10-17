"""ToastNotificationDispatcher tests (Phase 12).

Dispatch must never raise (it runs inline in the real-time Gmail sync
path) and must persist a ``Notification`` + request exactly one toast per
dispatch call when enabled.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tests.fakes.notifications import FakeNotificationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.services.notification_dispatch import (
    ToastNotificationDispatcher,
)
from insightflow.domain import (
    EventId,
    IntelligenceEvent,
    IntelligenceEventCreated,
    Priority,
    SourceConfiguration,
    SourceReference,
    SourceType,
    Topic,
    TopicId,
)


def _topic(store: InMemoryStore, *, name: str = "TRUMP") -> Topic:
    topic = Topic.create(
        name=name,
        source_configuration=SourceConfiguration(
            source_type=SourceType.GENERIC, source_id="src", source_identifier=name
        ),
    )
    with store.unit_of_work_factory() as uow:
        uow.topics.add(topic)
        uow.commit()
    return topic


def _create_event(
    store: InMemoryStore,
    *,
    topic_id: str | None,
    title: str | None,
    priority: Priority | None = None,
) -> IntelligenceEventCreated:
    event = IntelligenceEvent.create(
        source=SourceReference(
            source_type=SourceType.GENERIC, source_id="src", external_id="ext-1"
        ),
        title=title,
        priority=priority,
    )
    if topic_id is not None:
        event.topic_id = TopicId(topic_id)
    with store.unit_of_work_factory() as uow:
        uow.events.add(event)
        uow.commit()
    return IntelligenceEventCreated(
        event_id=event.id,
        topic_id=TopicId(topic_id) if topic_id else None,
        occurred_at=datetime.now(UTC),
    )


def test_dispatch_persists_notification_and_requests_toast() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(
        store, topic_id=topic.id.value, title="Trump signals de-escalation on Iran"
    )
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert len(port.requests) == 1
    request = port.requests[0]
    assert request.title == "InsightFlow AI — TRUMP"
    assert request.body == "Trump signals de-escalation on Iran"
    assert request.event_id == domain_event.event_id.value

    with store.unit_of_work_factory() as uow:
        notifications = uow.notifications.list_recent()
    assert len(notifications) == 1
    assert notifications[0].title == "Trump signals de-escalation on Iran"
    assert notifications[0].summary == "TRUMP"


def test_dispatch_skips_entirely_when_disabled() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(store, topic_id=topic.id.value, title="Subject")
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=False
    )

    dispatcher.dispatch(domain_event)

    assert port.requests == []
    with store.unit_of_work_factory() as uow:
        assert uow.notifications.list_recent() == []


def test_dispatch_without_topic_uses_app_name_only() -> None:
    store = InMemoryStore()
    domain_event = _create_event(store, topic_id=None, title="Subject line")
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert port.requests[0].title == "InsightFlow AI"
    assert port.requests[0].body == "Subject line"


def test_dispatch_empty_subject_uses_fallback() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(store, topic_id=topic.id.value, title=None)
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    assert port.requests[0].body == "New email received"


def test_dispatch_truncates_long_subject() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    long_subject = "x" * 500
    domain_event = _create_event(store, topic_id=topic.id.value, title=long_subject)
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    body = port.requests[0].body
    assert len(body) <= 200
    assert body.endswith("…")


def test_dispatch_survives_notification_port_failure() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(store, topic_id=topic.id.value, title="Subject")
    port = FakeNotificationPort(error=RuntimeError("toast backend unavailable"))
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)  # must not raise

    # The Notification record is still persisted even though delivery failed.
    with store.unit_of_work_factory() as uow:
        assert len(uow.notifications.list_recent()) == 1


def test_dispatch_defaults_priority_to_medium_when_event_has_none() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(store, topic_id=topic.id.value, title="Subject")
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    with store.unit_of_work_factory() as uow:
        notification = uow.notifications.list_recent()[0]
    assert notification.priority is Priority.MEDIUM


def test_dispatch_uses_event_priority_when_set() -> None:
    store = InMemoryStore()
    topic = _topic(store)
    domain_event = _create_event(
        store, topic_id=topic.id.value, title="Subject", priority=Priority.CRITICAL
    )
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(domain_event)

    with store.unit_of_work_factory() as uow:
        notification = uow.notifications.list_recent()[0]
    assert notification.priority is Priority.CRITICAL


def test_dispatch_missing_event_is_a_safe_noop() -> None:
    store = InMemoryStore()
    port = FakeNotificationPort()
    dispatcher = ToastNotificationDispatcher(
        store.unit_of_work_factory, port, enabled=True
    )

    dispatcher.dispatch(
        IntelligenceEventCreated(
            event_id=EventId.generate(), topic_id=None, occurred_at=datetime.now(UTC)
        )
    )

    assert port.requests == []
