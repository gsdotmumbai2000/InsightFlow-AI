"""Dashboard summary use-case unit tests."""

from __future__ import annotations

from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import EventId, Notification, Priority


def test_empty_dashboard(use_cases: ApplicationUseCases) -> None:
    summary = use_cases.get_dashboard_summary.execute()
    assert summary.enabled_topic_count == 0
    assert summary.total_topic_count == 0
    assert summary.recent_event_count == 0
    assert summary.high_priority_event_count == 0
    assert summary.unprocessed_event_count == 0
    assert summary.pending_notification_count == 0
    assert summary.monitoring_status is None
    assert summary.recent_events == ()
    assert summary.recent_notifications == ()


def test_populated_dashboard(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Dash Topic",
            source_type="GMAIL",
            source_id="acct-1",
            source_identifier="Label_dash",
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-dash",
            title="Priority item",
            priority="HIGH",
        )
    )
    notification = Notification.create(
        event_id=EventId(event.id),
        priority=Priority.HIGH,
        title="Dash alert",
    )
    with store.unit_of_work_factory() as uow:
        uow.notifications.add(notification)
        uow.commit()

    summary = use_cases.get_dashboard_summary.execute()
    assert summary.enabled_topic_count == 1
    assert summary.total_topic_count == 1
    assert summary.recent_event_count == 1
    assert summary.high_priority_event_count == 1
    assert summary.unprocessed_event_count == 1
    assert summary.pending_notification_count == 1
    assert len(summary.recent_events) == 1
    assert len(summary.recent_notifications) == 1
    assert summary.monitoring_status is None
