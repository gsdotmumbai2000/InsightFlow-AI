"""Intelligence event use-case unit tests."""

from __future__ import annotations

import pytest

from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
)
from insightflow.application.exceptions import (
    DuplicateEventError,
    EventNotFoundError,
    InvalidOperationError,
)
from insightflow.application.use_cases import ApplicationUseCases


def _topic(use_cases: ApplicationUseCases) -> str:
    return use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Topic",
            source_type="GMAIL",
            source_id="acct-1",
            source_identifier="Label_1",
        )
    ).id


def _event_request(**overrides: object) -> CreateIntelligenceEventRequest:
    payload: dict[str, object] = {
        "source_type": "GMAIL",
        "source_id": "acct-1",
        "external_id": "msg-1",
        "title": "Headline",
        "priority": "HIGH",
    }
    payload.update(overrides)
    return CreateIntelligenceEventRequest(**payload)  # type: ignore[arg-type]


def test_create_get_list_events(use_cases: ApplicationUseCases) -> None:
    topic_id = _topic(use_cases)
    created = use_cases.create_intelligence_event.execute(
        _event_request(topic_id=topic_id)
    )
    assert created.status == "RECEIVED"
    loaded = use_cases.get_intelligence_event.execute(created.id)
    assert loaded.id == created.id
    assert len(use_cases.list_recent_intelligence_events.execute()) == 1
    assert len(use_cases.list_events_by_topic.execute(topic_id)) == 1


def test_duplicate_event(use_cases: ApplicationUseCases) -> None:
    use_cases.create_intelligence_event.execute(_event_request())
    with pytest.raises(DuplicateEventError):
        use_cases.create_intelligence_event.execute(_event_request(title="Other"))


def test_valid_state_transitions(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_intelligence_event.execute(_event_request())
    processing = use_cases.mark_event_processing.execute(created.id)
    assert processing.status == "AI_PROCESSING"
    completed = use_cases.mark_event_completed.execute(created.id)
    assert completed.status == "COMPLETED"


def test_invalid_state_transition(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_intelligence_event.execute(_event_request())
    with pytest.raises(InvalidOperationError):
        use_cases.mark_event_completed.execute(created.id)


def test_mark_failed_and_ignored(use_cases: ApplicationUseCases) -> None:
    failed = use_cases.create_intelligence_event.execute(
        _event_request(external_id="msg-fail")
    )
    assert use_cases.mark_event_failed.execute(failed.id).status == "FAILED"
    ignored = use_cases.create_intelligence_event.execute(
        _event_request(external_id="msg-ignore")
    )
    assert use_cases.mark_event_ignored.execute(ignored.id).status == "IGNORED"


def test_event_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(EventNotFoundError):
        use_cases.get_intelligence_event.execute("missing-event")
