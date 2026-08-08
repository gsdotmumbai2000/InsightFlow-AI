"""Topic use-case unit tests."""

from __future__ import annotations

import pytest

from insightflow.application.dto.models import CreateTopicRequest, UpdateTopicRequest
from insightflow.application.exceptions import (
    ApplicationValidationError,
    DuplicateTopicError,
    InvalidOperationError,
    TopicNotFoundError,
)
from insightflow.application.use_cases import ApplicationUseCases


def _create_request(**overrides: object) -> CreateTopicRequest:
    payload: dict[str, object] = {
        "name": "Markets",
        "source_type": "GMAIL",
        "source_id": "acct-1",
        "source_identifier": "Label_1",
        "description": "Watch markets",
    }
    payload.update(overrides)
    return CreateTopicRequest(**payload)  # type: ignore[arg-type]


def test_create_get_list_topic(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_topic.execute(_create_request())
    assert created.name == "Markets"
    assert created.enabled is True
    loaded = use_cases.get_topic.execute(created.id)
    assert loaded.id == created.id
    listed = use_cases.list_topics.execute()
    assert len(listed) == 1


def test_duplicate_topic(use_cases: ApplicationUseCases) -> None:
    use_cases.create_topic.execute(_create_request())
    with pytest.raises(DuplicateTopicError):
        use_cases.create_topic.execute(_create_request(name="Other"))


def test_update_topic(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_topic.execute(_create_request())
    updated = use_cases.update_topic.execute(
        UpdateTopicRequest(topic_id=created.id, name="Renamed", description="New")
    )
    assert updated.name == "Renamed"
    assert updated.description == "New"


def test_enable_disable_pause_resume(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_topic.execute(_create_request())
    disabled = use_cases.disable_topic.execute(created.id)
    assert disabled.enabled is False
    with pytest.raises(InvalidOperationError):
        use_cases.pause_topic.execute(created.id)
    enabled = use_cases.enable_topic.execute(created.id)
    assert enabled.enabled is True
    paused = use_cases.pause_topic.execute(created.id)
    assert paused.status == "PAUSED"
    resumed = use_cases.resume_topic.execute(created.id)
    assert resumed.enabled is True


def test_topic_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(TopicNotFoundError):
        use_cases.get_topic.execute("missing-topic")


def test_invalid_source_type(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.create_topic.execute(_create_request(source_type="NOT_A_SOURCE"))


def test_invalid_update_name(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_topic.execute(_create_request())
    with pytest.raises(ApplicationValidationError):
        use_cases.update_topic.execute(
            UpdateTopicRequest(topic_id=created.id, name="   ")
        )
