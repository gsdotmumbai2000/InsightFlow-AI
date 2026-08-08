"""Topic entity tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from insightflow.domain import (
    DomainValidationError,
    InvalidStateTransitionError,
    SourceConfiguration,
    SourceType,
    Topic,
    TopicStatus,
)


def _source() -> SourceConfiguration:
    return SourceConfiguration(
        source_type=SourceType.GMAIL,
        source_id="account-1",
        source_identifier="Label_123",
    )


def test_topic_valid_creation() -> None:
    topic = Topic.create(name="Geopolitics Watch", source_configuration=_source())
    assert topic.name == "Geopolitics Watch"
    assert topic.status is TopicStatus.ENABLED
    assert topic.enabled is True
    assert topic.source_configuration.source_identifier == "Label_123"


def test_topic_empty_name_rejected() -> None:
    with pytest.raises(DomainValidationError, match="name"):
        Topic.create(name="   ", source_configuration=_source())


def test_topic_enable_disable() -> None:
    topic = Topic.create(name="Markets", source_configuration=_source())
    topic.disable(at=datetime(2026, 1, 1, tzinfo=UTC))
    assert topic.status is TopicStatus.DISABLED
    assert topic.enabled is False
    topic.enable(at=datetime(2026, 1, 2, tzinfo=UTC))
    assert topic.status is TopicStatus.ENABLED


def test_topic_pause_resume() -> None:
    topic = Topic.create(name="Markets", source_configuration=_source())
    topic.pause()
    assert topic.status is TopicStatus.PAUSED
    topic.resume()
    assert topic.status is TopicStatus.ENABLED


def test_disabled_topic_cannot_pause() -> None:
    topic = Topic.create(name="Markets", source_configuration=_source())
    topic.disable()
    with pytest.raises(InvalidStateTransitionError):
        topic.pause()
