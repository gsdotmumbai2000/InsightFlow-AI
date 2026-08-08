"""Story entity — minimal grouping of related intelligence events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from insightflow.domain.enums import StoryStatus
from insightflow.domain.exceptions import InvalidStateTransitionError
from insightflow.domain.value_objects import EventId, StoryId, TopicId
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class Story:
    """Groups related intelligence events for later narrative/content use."""

    id: StoryId
    topic_id: TopicId | None
    title: str
    summary: str | None
    status: StoryStatus
    event_ids: tuple[EventId, ...]
    first_event_at: datetime | None
    last_event_at: datetime | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, "title")
        if self.summary is not None:
            self.summary = require_non_empty(self.summary, "summary")
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")
        if self.first_event_at is not None:
            self.first_event_at = require_aware_utc(
                self.first_event_at, "first_event_at"
            )
        if self.last_event_at is not None:
            self.last_event_at = require_aware_utc(self.last_event_at, "last_event_at")

    @classmethod
    def create(
        cls,
        *,
        title: str,
        topic_id: TopicId | None = None,
        summary: str | None = None,
        event_ids: tuple[EventId, ...] | list[EventId] = (),
        story_id: StoryId | None = None,
        created_at: datetime | None = None,
    ) -> Story:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        ids = tuple(event_ids)
        return cls(
            id=story_id or StoryId.generate(),
            topic_id=topic_id,
            title=title,
            summary=summary,
            status=StoryStatus.ACTIVE,
            event_ids=ids,
            first_event_at=timestamp if ids else None,
            last_event_at=timestamp if ids else None,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def add_event(
        self,
        event_id: EventId,
        *,
        at: datetime | None = None,
    ) -> None:
        if self.status is not StoryStatus.ACTIVE:
            raise InvalidStateTransitionError("Cannot add events to a closed story.")
        if event_id in self.event_ids:
            return
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.event_ids = (*self.event_ids, event_id)
        if self.first_event_at is None:
            self.first_event_at = timestamp
        self.last_event_at = timestamp
        self.updated_at = timestamp

    def close(self, *, at: datetime | None = None) -> None:
        if self.status is StoryStatus.CLOSED:
            return
        self.status = StoryStatus.CLOSED
        self.updated_at = require_aware_utc(at or utc_now(), "at")
