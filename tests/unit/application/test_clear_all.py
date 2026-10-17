"""Clear all notifications / intelligence events."""

from __future__ import annotations

import pytest
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.exceptions import DuplicateEventError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import EventId, Notification, Priority


def _event_request(external_id: str) -> CreateIntelligenceEventRequest:
    return CreateIntelligenceEventRequest(
        source_type="GMAIL",
        source_id="acct-1",
        external_id=external_id,
        title=f"Message {external_id}",
    )


def test_clear_all_intelligence_events_deletes_and_counts(
    use_cases: ApplicationUseCases,
) -> None:
    use_cases.create_intelligence_event.execute(_event_request("m1"))
    use_cases.create_intelligence_event.execute(_event_request("m2"))

    deleted = use_cases.clear_all_intelligence_events.execute()

    assert deleted == 2
    assert use_cases.list_recent_intelligence_events.execute(limit=100) == []


def test_cleared_message_is_not_ingested_again(
    use_cases: ApplicationUseCases,
) -> None:
    """Full sync re-reads recent Gmail messages on every Agent start; a
    cleared message must count as a duplicate, not come back."""
    use_cases.create_intelligence_event.execute(_event_request("m1"))
    use_cases.clear_all_intelligence_events.execute()

    with pytest.raises(DuplicateEventError):
        use_cases.create_intelligence_event.execute(_event_request("m1"))

    # A genuinely new message is still ingested.
    created = use_cases.create_intelligence_event.execute(_event_request("m2"))
    assert created.source.external_id == "m2"


def test_clear_all_with_no_events_is_a_no_op(use_cases: ApplicationUseCases) -> None:
    assert use_cases.clear_all_intelligence_events.execute() == 0


def test_clear_all_notifications_keeps_events(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(_event_request("m1"))
    with store.unit_of_work_factory() as uow:
        for index in range(3):
            uow.notifications.add(
                Notification.create(
                    event_id=EventId(event.id),
                    priority=Priority.MEDIUM,
                    title=f"Toast {index}",
                )
            )
        uow.commit()

    deleted = use_cases.clear_all_notifications.execute()

    assert deleted == 3
    assert use_cases.list_recent_notifications.execute(limit=100) == []
    assert use_cases.get_intelligence_event.execute(event.id).id == event.id
