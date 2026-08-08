"""Notification use-case unit tests."""

from __future__ import annotations

import pytest
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.exceptions import (
    InvalidOperationError,
    NotificationNotFoundError,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import EventId, Notification, Priority


def _seed_notification(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> Notification:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-n1",
            title="Notify",
        )
    )
    notification = Notification.create(
        event_id=EventId(event.id),
        priority=Priority.HIGH,
        title="Alert",
        summary="Something happened",
    )
    with store.unit_of_work_factory() as uow:
        uow.notifications.add(notification)
        uow.commit()
    return notification


def test_get_list_mark_displayed_dismissed(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    notification = _seed_notification(use_cases, store)
    loaded = use_cases.get_notification.execute(notification.id.value)
    assert loaded.title == "Alert"
    listed = use_cases.list_recent_notifications.execute()
    assert len(listed) == 1
    displayed = use_cases.mark_notification_displayed.execute(notification.id.value)
    assert displayed.status == "DISPLAYED"
    dismissed = use_cases.mark_notification_dismissed.execute(notification.id.value)
    assert dismissed.status == "DISMISSED"


def test_invalid_notification_transition(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    notification = _seed_notification(use_cases, store)
    use_cases.mark_notification_dismissed.execute(notification.id.value)
    with pytest.raises(InvalidOperationError):
        use_cases.mark_notification_displayed.execute(notification.id.value)


def test_notification_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(NotificationNotFoundError):
        use_cases.get_notification.execute("missing")
