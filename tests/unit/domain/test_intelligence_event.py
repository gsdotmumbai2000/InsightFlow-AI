"""IntelligenceEvent entity tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from insightflow.domain import (
    DomainValidationError,
    EventProcessingStatus,
    IntelligenceEvent,
    InvalidStateTransitionError,
    Priority,
    SourceReference,
    SourceType,
)


def _source() -> SourceReference:
    return SourceReference(
        source_type=SourceType.GMAIL,
        source_id="gmail-account",
        external_id="msg-1",
        thread_id="thread-1",
    )


def test_event_valid_creation() -> None:
    event = IntelligenceEvent.create(
        source=_source(),
        title="Headline",
        normalized_content="Body text",
        received_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    assert event.status is EventProcessingStatus.RECEIVED
    assert event.source.external_id == "msg-1"
    assert event.title == "Headline"


def test_event_naive_timestamp_rejected() -> None:
    with pytest.raises(DomainValidationError, match="timezone-aware"):
        IntelligenceEvent.create(
            source=_source(),
            received_at=datetime(2026, 1, 1, 12, 0),
        )


def test_event_state_transitions() -> None:
    event = IntelligenceEvent.create(source=_source())
    event.mark_processing()
    assert event.status is EventProcessingStatus.AI_PROCESSING
    event.mark_completed()
    assert event.status is EventProcessingStatus.COMPLETED
    assert event.is_terminal is True


def test_event_invalid_transition() -> None:
    event = IntelligenceEvent.create(source=_source())
    event.mark_ignored()
    with pytest.raises(InvalidStateTransitionError):
        event.mark_processing()


def test_event_mark_failed_and_ignored() -> None:
    event = IntelligenceEvent.create(source=_source())
    event.mark_failed()
    assert event.status is EventProcessingStatus.FAILED

    event2 = IntelligenceEvent.create(source=_source(), title="Other")
    event2.mark_ignored()
    assert event2.status is EventProcessingStatus.IGNORED


def test_event_assign_priority() -> None:
    event = IntelligenceEvent.create(source=_source())
    event.assign_priority(Priority.HIGH)
    assert event.priority is Priority.HIGH


def test_empty_source_external_id_rejected() -> None:
    with pytest.raises(DomainValidationError):
        SourceReference(
            source_type=SourceType.GENERIC,
            source_id="src",
            external_id="  ",
        )
