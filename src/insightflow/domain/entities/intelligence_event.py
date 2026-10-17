"""IntelligenceEvent entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from insightflow.domain.enums import EventProcessingStatus, Priority
from insightflow.domain.exceptions import InvalidStateTransitionError
from insightflow.domain.value_objects import (
    ContentHash,
    EventId,
    SourceReference,
    StoryId,
    TopicId,
)
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)

_TERMINAL_STATUSES = frozenset(
    {
        EventProcessingStatus.COMPLETED,
        EventProcessingStatus.DUPLICATE,
        EventProcessingStatus.IGNORED,
    }
)

_PROCESSING_SOURCES = frozenset(
    {
        EventProcessingStatus.RECEIVED,
        EventProcessingStatus.VALIDATING,
        EventProcessingStatus.NORMALIZED,
        EventProcessingStatus.TOPIC_RESOLVED,
        EventProcessingStatus.DEDUPLICATING,
        EventProcessingStatus.AI_PENDING,
        EventProcessingStatus.RETRY_PENDING,
        # Re-analysis (Phase 11) must be able to restart AI processing for an
        # event whose pipeline already reached a terminal state.
        EventProcessingStatus.COMPLETED,
        EventProcessingStatus.FAILED,
    }
)

_COMPLETION_SOURCES = frozenset(
    {
        EventProcessingStatus.AI_COMPLETED,
        EventProcessingStatus.PERSISTING,
        EventProcessingStatus.NOTIFICATION_PENDING,
        EventProcessingStatus.AI_PROCESSING,
    }
)

_FAILURE_BLOCKED = frozenset(
    {
        EventProcessingStatus.COMPLETED,
        EventProcessingStatus.DUPLICATE,
        EventProcessingStatus.IGNORED,
    }
)

_IGNORE_SOURCES = frozenset(
    {
        EventProcessingStatus.RECEIVED,
        EventProcessingStatus.VALIDATING,
        EventProcessingStatus.NORMALIZED,
        EventProcessingStatus.TOPIC_RESOLVED,
        EventProcessingStatus.DEDUPLICATING,
        EventProcessingStatus.AI_PENDING,
    }
)


@dataclass(slots=True)
class IntelligenceEvent:
    """One meaningful source occurrence, independent of provider SDKs."""

    id: EventId
    topic_id: TopicId | None
    source: SourceReference
    title: str | None
    normalized_content: str | None
    source_published_at: datetime | None
    received_at: datetime
    status: EventProcessingStatus
    priority: Priority | None
    content_hash: ContentHash | None
    story_id: StoryId | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.received_at = require_aware_utc(self.received_at, "received_at")
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")
        if self.source_published_at is not None:
            self.source_published_at = require_aware_utc(
                self.source_published_at, "source_published_at"
            )
        if self.title is not None:
            self.title = require_non_empty(self.title, "title")
        if self.normalized_content is not None:
            self.normalized_content = require_non_empty(
                self.normalized_content, "normalized_content"
            )

    @classmethod
    def create(
        cls,
        *,
        source: SourceReference,
        topic_id: TopicId | None = None,
        title: str | None = None,
        normalized_content: str | None = None,
        source_published_at: datetime | None = None,
        received_at: datetime | None = None,
        priority: Priority | None = None,
        content_hash: ContentHash | None = None,
        story_id: StoryId | None = None,
        event_id: EventId | None = None,
        created_at: datetime | None = None,
    ) -> IntelligenceEvent:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        received = require_aware_utc(received_at or timestamp, "received_at")
        return cls(
            id=event_id or EventId.generate(),
            topic_id=topic_id,
            source=source,
            title=title,
            normalized_content=normalized_content,
            source_published_at=source_published_at,
            received_at=received,
            status=EventProcessingStatus.RECEIVED,
            priority=priority,
            content_hash=content_hash,
            story_id=story_id,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _transition(
        self,
        new_status: EventProcessingStatus,
        *,
        at: datetime | None,
        allowed_from: frozenset[EventProcessingStatus],
        action: str,
    ) -> None:
        if self.status is new_status:
            return
        if self.status not in allowed_from:
            raise InvalidStateTransitionError(
                f"Cannot {action} event in status {self.status.value}."
            )
        self.status = new_status
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_received(self, *, at: datetime | None = None) -> None:
        if self.status is EventProcessingStatus.RECEIVED:
            return
        raise InvalidStateTransitionError(
            f"Cannot mark_received from status {self.status.value}."
        )

    def cancel_ai_processing(self, *, at: datetime | None = None) -> None:
        """Return a not-yet-analyzed event from AI_PROCESSING to RECEIVED.

        Used when the user turns automatic AI analysis off: the waiting
        backlog is cancelled rather than analyzed (and billed) later.
        """
        self._transition(
            EventProcessingStatus.RECEIVED,
            at=at,
            allowed_from=frozenset({EventProcessingStatus.AI_PROCESSING}),
            action="cancel_ai_processing",
        )

    def mark_processing(self, *, at: datetime | None = None) -> None:
        self._transition(
            EventProcessingStatus.AI_PROCESSING,
            at=at,
            allowed_from=_PROCESSING_SOURCES,
            action="mark_processing",
        )

    def mark_completed(self, *, at: datetime | None = None) -> None:
        self._transition(
            EventProcessingStatus.COMPLETED,
            at=at,
            allowed_from=_COMPLETION_SOURCES,
            action="mark_completed",
        )

    def mark_failed(self, *, at: datetime | None = None) -> None:
        if self.status in _FAILURE_BLOCKED:
            raise InvalidStateTransitionError(
                f"Cannot mark_failed from terminal status {self.status.value}."
            )
        if self.status is EventProcessingStatus.FAILED:
            return
        self.status = EventProcessingStatus.FAILED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_ignored(self, *, at: datetime | None = None) -> None:
        self._transition(
            EventProcessingStatus.IGNORED,
            at=at,
            allowed_from=_IGNORE_SOURCES,
            action="mark_ignored",
        )

    def mark_duplicate(self, *, at: datetime | None = None) -> None:
        self._transition(
            EventProcessingStatus.DUPLICATE,
            at=at,
            allowed_from=frozenset(
                {
                    EventProcessingStatus.RECEIVED,
                    EventProcessingStatus.DEDUPLICATING,
                    EventProcessingStatus.TOPIC_RESOLVED,
                }
            ),
            action="mark_duplicate",
        )

    def assign_priority(
        self, priority: Priority, *, at: datetime | None = None
    ) -> None:
        self.priority = priority
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def assign_story(self, story_id: StoryId, *, at: datetime | None = None) -> None:
        self.story_id = story_id
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES
