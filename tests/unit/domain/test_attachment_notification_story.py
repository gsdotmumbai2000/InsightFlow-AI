"""Attachment, Notification, Story, and identifier tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from insightflow.domain import (
    Attachment,
    DomainValidationError,
    EventId,
    IntelligenceEventCreated,
    InvalidStateTransitionError,
    Notification,
    NotificationStatus,
    Priority,
    Story,
    StoryStatus,
    TopicId,
)


def test_attachment_valid_creation() -> None:
    attachment = Attachment.create(
        event_id=EventId.generate(),
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )
    assert attachment.filename == "report.pdf"
    assert attachment.size_bytes == 1024


def test_attachment_empty_filename_rejected() -> None:
    with pytest.raises(DomainValidationError, match="filename"):
        Attachment.create(event_id=EventId.generate(), filename=" ")


def test_attachment_negative_size_rejected() -> None:
    with pytest.raises(DomainValidationError, match="negative"):
        Attachment.create(
            event_id=EventId.generate(),
            filename="a.pdf",
            size_bytes=-1,
        )


def test_notification_transitions() -> None:
    notification = Notification.create(
        event_id=EventId.generate(),
        priority=Priority.HIGH,
        title="Alert",
        summary="Something happened",
    )
    assert notification.status is NotificationStatus.PENDING
    notification.mark_displayed(at=datetime(2026, 1, 1, tzinfo=UTC))
    assert notification.status is NotificationStatus.DISPLAYED
    assert notification.displayed_at is not None
    notification.mark_dismissed(at=datetime(2026, 1, 2, tzinfo=UTC))
    assert notification.status is NotificationStatus.DISMISSED


def test_notification_failure_transition() -> None:
    notification = Notification.create(
        event_id=EventId.generate(),
        priority=Priority.MEDIUM,
        title="Alert",
    )
    notification.mark_failed(reason="toast provider unavailable")
    assert notification.status is NotificationStatus.FAILED
    with pytest.raises(InvalidStateTransitionError):
        notification.mark_displayed()


def test_story_creation_and_close() -> None:
    event_id = EventId.generate()
    story = Story.create(title="Developing situation", topic_id=TopicId.generate())
    story.add_event(event_id)
    assert event_id in story.event_ids
    assert story.status is StoryStatus.ACTIVE
    story.close()
    assert story.status is StoryStatus.CLOSED
    with pytest.raises(InvalidStateTransitionError):
        story.add_event(EventId.generate())


def test_identifier_equality_and_immutability() -> None:
    topic_a = TopicId.generate()
    topic_b = TopicId(topic_a.value)
    assert topic_a == topic_b
    assert hash(topic_a) == hash(topic_b)
    with pytest.raises(AttributeError):
        topic_a.value = "mutated"  # type: ignore[misc]


def test_domain_event_definition() -> None:
    event = IntelligenceEventCreated(
        event_id=EventId.generate(),
        topic_id=TopicId.generate(),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert event.topic_id is not None
    with pytest.raises(DomainValidationError):
        IntelligenceEventCreated(
            event_id=EventId.generate(),
            topic_id=None,
            occurred_at=datetime(2026, 1, 1),
        )
