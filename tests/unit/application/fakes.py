"""In-memory UnitOfWork and repositories for application unit tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import cast

from insightflow.application.exceptions import DuplicateEntityError
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    AIAnalysis,
    AIAnalysisId,
    AIProfile,
    AIProfileId,
    Attachment,
    AttachmentId,
    EventId,
    IntelligenceEvent,
    Notification,
    NotificationId,
    NotificationStatus,
    Story,
    StoryId,
    Topic,
    TopicId,
    TopicStatus,
)


def _clone[T](value: T) -> T:
    return deepcopy(value)


@dataclass
class InMemoryTopicRepository:
    _items: dict[str, Topic] = field(default_factory=dict)

    def add(self, topic: Topic) -> None:
        key = topic.id.value
        if key in self._items:
            raise DuplicateEntityError(f"Topic already exists: {key}")
        for existing in self._items.values():
            if (
                existing.source_configuration.source_id
                == topic.source_configuration.source_id
                and existing.source_configuration.source_identifier
                == topic.source_configuration.source_identifier
            ):
                raise DuplicateEntityError(
                    "Topic already exists for source identifier."
                )
        self._items[key] = _clone(topic)

    def get(self, topic_id: TopicId) -> Topic | None:
        topic = self._items.get(topic_id.value)
        return _clone(topic) if topic is not None else None

    def update(self, topic: Topic) -> None:
        if topic.id.value not in self._items:
            raise KeyError(f"Topic not found: {topic.id.value}")
        self._items[topic.id.value] = _clone(topic)

    def list_all(self) -> list[Topic]:
        return [_clone(item) for item in self._items.values()]

    def list_enabled(self) -> list[Topic]:
        return [
            _clone(item)
            for item in self._items.values()
            if item.status is TopicStatus.ENABLED
        ]

    def find_by_source_identifier(
        self, *, source_id: str, source_identifier: str
    ) -> Topic | None:
        for item in self._items.values():
            if (
                item.source_configuration.source_id == source_id
                and item.source_configuration.source_identifier == source_identifier
            ):
                return _clone(item)
        return None

    def delete(self, topic_id: TopicId) -> None:
        self._items.pop(topic_id.value, None)


@dataclass
class InMemoryIntelligenceEventRepository:
    _items: dict[str, IntelligenceEvent] = field(default_factory=dict)

    def add(self, event: IntelligenceEvent) -> None:
        key = event.id.value
        if key in self._items:
            raise DuplicateEntityError(f"Event already exists: {key}")
        for existing in self._items.values():
            if (
                existing.source.source_id == event.source.source_id
                and existing.source.external_id == event.source.external_id
            ):
                raise DuplicateEntityError(
                    "Intelligence event already exists for source identity."
                )
        self._items[key] = _clone(event)

    def get(self, event_id: EventId) -> IntelligenceEvent | None:
        event = self._items.get(event_id.value)
        return _clone(event) if event is not None else None

    def update(self, event: IntelligenceEvent) -> None:
        if event.id.value not in self._items:
            raise KeyError(f"Event not found: {event.id.value}")
        self._items[event.id.value] = _clone(event)

    def find_by_external_id(
        self, *, source_id: str, external_id: str
    ) -> IntelligenceEvent | None:
        for item in self._items.values():
            if (
                item.source.source_id == source_id
                and item.source.external_id == external_id
            ):
                return _clone(item)
        return None

    def list_by_topic(
        self, topic_id: TopicId, *, limit: int = 100
    ) -> list[IntelligenceEvent]:
        items = [
            item
            for item in self._items.values()
            if item.topic_id is not None and item.topic_id.value == topic_id.value
        ]
        items.sort(key=lambda event: event.received_at, reverse=True)
        return [_clone(item) for item in items[:limit]]

    def list_recent(self, *, limit: int = 100) -> list[IntelligenceEvent]:
        items = sorted(
            self._items.values(),
            key=lambda event: event.received_at,
            reverse=True,
        )
        return [_clone(item) for item in items[:limit]]


@dataclass
class InMemoryAIProfileRepository:
    _items: dict[str, AIProfile] = field(default_factory=dict)

    def add(self, profile: AIProfile) -> None:
        if profile.id.value in self._items:
            raise DuplicateEntityError(f"AI profile already exists: {profile.id.value}")
        self._items[profile.id.value] = _clone(profile)

    def get(self, profile_id: AIProfileId) -> AIProfile | None:
        profile = self._items.get(profile_id.value)
        return _clone(profile) if profile is not None else None

    def update(self, profile: AIProfile) -> None:
        if profile.id.value not in self._items:
            raise KeyError(f"AI profile not found: {profile.id.value}")
        self._items[profile.id.value] = _clone(profile)

    def list_all(self) -> list[AIProfile]:
        return [_clone(item) for item in self._items.values()]


@dataclass
class InMemoryAIAnalysisRepository:
    _items: dict[str, AIAnalysis] = field(default_factory=dict)

    def add(self, analysis: AIAnalysis) -> None:
        if analysis.id.value in self._items:
            raise DuplicateEntityError(
                f"AI analysis already exists: {analysis.id.value}"
            )
        self._items[analysis.id.value] = _clone(analysis)

    def get(self, analysis_id: AIAnalysisId) -> AIAnalysis | None:
        analysis = self._items.get(analysis_id.value)
        return _clone(analysis) if analysis is not None else None

    def list_by_event(self, event_id: EventId) -> list[AIAnalysis]:
        items = [
            item
            for item in self._items.values()
            if item.event_id.value == event_id.value
        ]
        items.sort(key=lambda analysis: analysis.created_at)
        return [_clone(item) for item in items]

    def find_latest_by_event(self, event_id: EventId) -> AIAnalysis | None:
        items = self.list_by_event(event_id)
        return items[-1] if items else None


@dataclass
class InMemoryAttachmentRepository:
    _items: dict[str, Attachment] = field(default_factory=dict)

    def add(self, attachment: Attachment) -> None:
        if attachment.id.value in self._items:
            raise DuplicateEntityError(
                f"Attachment already exists: {attachment.id.value}"
            )
        self._items[attachment.id.value] = _clone(attachment)

    def get(self, attachment_id: AttachmentId) -> Attachment | None:
        attachment = self._items.get(attachment_id.value)
        return _clone(attachment) if attachment is not None else None

    def update(self, attachment: Attachment) -> None:
        if attachment.id.value not in self._items:
            raise KeyError(f"Attachment not found: {attachment.id.value}")
        self._items[attachment.id.value] = _clone(attachment)

    def list_by_event(self, event_id: EventId) -> list[Attachment]:
        return [
            _clone(item)
            for item in self._items.values()
            if item.event_id.value == event_id.value
        ]


@dataclass
class InMemoryNotificationRepository:
    _items: dict[str, Notification] = field(default_factory=dict)

    def add(self, notification: Notification) -> None:
        if notification.id.value in self._items:
            raise DuplicateEntityError(
                f"Notification already exists: {notification.id.value}"
            )
        self._items[notification.id.value] = _clone(notification)

    def get(self, notification_id: NotificationId) -> Notification | None:
        notification = self._items.get(notification_id.value)
        return _clone(notification) if notification is not None else None

    def update(self, notification: Notification) -> None:
        if notification.id.value not in self._items:
            raise KeyError(f"Notification not found: {notification.id.value}")
        self._items[notification.id.value] = _clone(notification)

    def list_pending(self) -> list[Notification]:
        return [
            _clone(item)
            for item in self._items.values()
            if item.status is NotificationStatus.PENDING
        ]

    def list_recent(self, *, limit: int = 100) -> list[Notification]:
        items = sorted(
            self._items.values(),
            key=lambda notification: notification.created_at,
            reverse=True,
        )
        return [_clone(item) for item in items[:limit]]


@dataclass
class InMemoryStoryRepository:
    _items: dict[str, Story] = field(default_factory=dict)

    def add(self, story: Story) -> None:
        if story.id.value in self._items:
            raise DuplicateEntityError(f"Story already exists: {story.id.value}")
        self._items[story.id.value] = _clone(story)

    def get(self, story_id: StoryId) -> Story | None:
        story = self._items.get(story_id.value)
        return _clone(story) if story is not None else None

    def update(self, story: Story) -> None:
        if story.id.value not in self._items:
            raise KeyError(f"Story not found: {story.id.value}")
        self._items[story.id.value] = _clone(story)

    def list_by_topic(self, topic_id: TopicId) -> list[Story]:
        return [
            _clone(item)
            for item in self._items.values()
            if item.topic_id is not None and item.topic_id.value == topic_id.value
        ]


@dataclass
class InMemoryUnitOfWork:
    """Shared in-memory stores across UoW instances created by one factory."""

    topics: InMemoryTopicRepository
    events: InMemoryIntelligenceEventRepository
    profiles: InMemoryAIProfileRepository
    analyses: InMemoryAIAnalysisRepository
    attachments: InMemoryAttachmentRepository
    notifications: InMemoryNotificationRepository
    stories: InMemoryStoryRepository
    _committed: bool = False
    _active: bool = False

    def __enter__(self) -> InMemoryUnitOfWork:
        self._active = True
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        if exc_type is not None and not self._committed:
            self.rollback()
        self._active = False

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        # Mutations already applied to shared stores; tests seed intentionally.
        self._committed = False


@dataclass
class InMemoryStore:
    """Factory backing store shared by all UoW instances in a test."""

    topics: InMemoryTopicRepository = field(default_factory=InMemoryTopicRepository)
    events: InMemoryIntelligenceEventRepository = field(
        default_factory=InMemoryIntelligenceEventRepository
    )
    profiles: InMemoryAIProfileRepository = field(
        default_factory=InMemoryAIProfileRepository
    )
    analyses: InMemoryAIAnalysisRepository = field(
        default_factory=InMemoryAIAnalysisRepository
    )
    attachments: InMemoryAttachmentRepository = field(
        default_factory=InMemoryAttachmentRepository
    )
    notifications: InMemoryNotificationRepository = field(
        default_factory=InMemoryNotificationRepository
    )
    stories: InMemoryStoryRepository = field(default_factory=InMemoryStoryRepository)

    def unit_of_work_factory(self) -> UnitOfWork:
        return cast(
            UnitOfWork,
            InMemoryUnitOfWork(
                topics=self.topics,
                events=self.events,
                profiles=self.profiles,
                analyses=self.analyses,
                attachments=self.attachments,
                notifications=self.notifications,
                stories=self.stories,
            ),
        )
