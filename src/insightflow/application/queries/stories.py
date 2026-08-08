"""Story read use cases."""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope, use_case_scope
from insightflow.application.dto.mappers import event_to_dto, story_to_dto
from insightflow.application.dto.models import IntelligenceEventDto, StoryDto
from insightflow.application.exceptions import (
    StoryNotFoundError,
    TopicNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import StoryId, TopicId


class GetStoryUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, story_id: str) -> StoryDto:
        with (
            use_case_scope("GetStory"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            story = uow.stories.get(StoryId(story_id))
            if story is None:
                raise StoryNotFoundError(f"Story not found: {story_id}")
            return story_to_dto(story)


class ListStoriesUseCase:
    """List stories for a topic (repository supports topic-scoped listing only)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> list[StoryDto]:
        with (
            use_case_scope("ListStories"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            if uow.topics.get(TopicId(topic_id)) is None:
                raise TopicNotFoundError(f"Topic not found: {topic_id}")
            stories = uow.stories.list_by_topic(TopicId(topic_id))
            return [story_to_dto(story) for story in stories]


class GetStoryEventsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, story_id: str) -> list[IntelligenceEventDto]:
        with (
            use_case_scope("GetStoryEvents"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            story = uow.stories.get(StoryId(story_id))
            if story is None:
                raise StoryNotFoundError(f"Story not found: {story_id}")
            events: list[IntelligenceEventDto] = []
            for event_id in story.event_ids:
                event = uow.events.get(event_id)
                if event is not None:
                    events.append(event_to_dto(event))
            return events
