"""Story use-case unit tests."""

from __future__ import annotations

import pytest
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
)
from insightflow.application.exceptions import StoryNotFoundError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import EventId, Story, TopicId


def test_get_list_story_events(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Story Topic",
            source_type="GMAIL",
            source_id="acct-1",
            source_identifier="Label_story",
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-story",
            topic_id=topic.id,
            title="Story event",
        )
    )
    story = Story.create(
        title="Narrative",
        topic_id=TopicId(topic.id),
        event_ids=(EventId(event.id),),
    )
    with store.unit_of_work_factory() as uow:
        uow.stories.add(story)
        uow.commit()

    loaded = use_cases.get_story.execute(story.id.value)
    assert loaded.title == "Narrative"
    listed = use_cases.list_stories.execute(topic.id)
    assert len(listed) == 1
    events = use_cases.get_story_events.execute(story.id.value)
    assert len(events) == 1
    assert events[0].id == event.id


def test_story_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(StoryNotFoundError):
        use_cases.get_story.execute("missing")
