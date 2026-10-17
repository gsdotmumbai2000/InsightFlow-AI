"""Repository and unit-of-work ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from insightflow.domain import (
    AIAnalysis,
    AIAnalysisId,
    AIProfile,
    AIProfileId,
    Attachment,
    AttachmentId,
    EventId,
    EventProcessingStatus,
    IntelligenceEvent,
    MonitoringDesiredStatus,
    MonitoringState,
    MonitoringStateId,
    Notification,
    NotificationId,
    SourceType,
    Story,
    StoryId,
    Topic,
    TopicId,
)


@runtime_checkable
class TopicRepository(Protocol):
    def add(self, topic: Topic) -> None: ...
    def get(self, topic_id: TopicId) -> Topic | None: ...
    def update(self, topic: Topic) -> None: ...
    def list_all(self) -> list[Topic]: ...
    def list_enabled(self) -> list[Topic]: ...
    def find_by_source_identifier(
        self, *, source_id: str, source_identifier: str
    ) -> Topic | None: ...
    def delete(self, topic_id: TopicId) -> None: ...


@runtime_checkable
class IntelligenceEventRepository(Protocol):
    def add(self, event: IntelligenceEvent) -> None: ...
    def get(self, event_id: EventId) -> IntelligenceEvent | None: ...
    def update(self, event: IntelligenceEvent) -> None: ...
    def find_by_external_id(
        self, *, source_id: str, external_id: str
    ) -> IntelligenceEvent | None: ...
    def list_by_topic(
        self, topic_id: TopicId, *, limit: int = 100
    ) -> list[IntelligenceEvent]: ...
    def list_recent(self, *, limit: int = 100) -> list[IntelligenceEvent]: ...
    def list_by_status(
        self, status: EventProcessingStatus, *, limit: int = 100
    ) -> list[IntelligenceEvent]:
        """Events in ``status``, least recently updated first."""
        ...

    def delete_all(self) -> int:
        """Delete every event (analyses, notifications, attachments cascade).

        Each deleted event's source identity is remembered, so
        ``was_cleared`` stops it from being ingested again. Returns how many
        events were deleted.
        """
        ...

    def was_cleared(self, *, source_id: str, external_id: str) -> bool: ...


@runtime_checkable
class AIProfileRepository(Protocol):
    def add(self, profile: AIProfile) -> None: ...
    def get(self, profile_id: AIProfileId) -> AIProfile | None:
        """``None`` for unknown and for deleted profiles."""
        ...

    def update(self, profile: AIProfile) -> None: ...
    def list_all(self) -> list[AIProfile]:
        """Every profile except deleted ones."""
        ...

    def delete(self, profile_id: AIProfileId) -> None:
        """Hide the profile everywhere; analyses that used it are kept."""
        ...


@runtime_checkable
class AIAnalysisRepository(Protocol):
    def add(self, analysis: AIAnalysis) -> None: ...
    def get(self, analysis_id: AIAnalysisId) -> AIAnalysis | None: ...
    def list_by_event(self, event_id: EventId) -> list[AIAnalysis]: ...
    def find_latest_by_event(self, event_id: EventId) -> AIAnalysis | None: ...


@runtime_checkable
class AttachmentRepository(Protocol):
    def add(self, attachment: Attachment) -> None: ...
    def get(self, attachment_id: AttachmentId) -> Attachment | None: ...
    def update(self, attachment: Attachment) -> None: ...
    def list_by_event(self, event_id: EventId) -> list[Attachment]: ...


@runtime_checkable
class NotificationRepository(Protocol):
    def add(self, notification: Notification) -> None: ...
    def get(self, notification_id: NotificationId) -> Notification | None: ...
    def update(self, notification: Notification) -> None: ...
    def list_pending(self) -> list[Notification]: ...
    def list_recent(self, *, limit: int = 100) -> list[Notification]: ...
    def delete_all(self) -> int:
        """Delete every notification; returns how many were deleted."""
        ...


@runtime_checkable
class StoryRepository(Protocol):
    def add(self, story: Story) -> None: ...
    def get(self, story_id: StoryId) -> Story | None: ...
    def update(self, story: Story) -> None: ...
    def list_by_topic(self, topic_id: TopicId) -> list[Story]: ...


@runtime_checkable
class MonitoringStateRepository(Protocol):
    """Real-time monitoring cursor persistence (Phase 10)."""

    def add(self, state: MonitoringState) -> None: ...
    def get(self, state_id: MonitoringStateId) -> MonitoringState | None: ...
    def get_by_account(
        self, *, account_id: str, provider: SourceType
    ) -> MonitoringState | None: ...
    def update(self, state: MonitoringState) -> None: ...


@runtime_checkable
class MonitoringControlRepository(Protocol):
    """Persisted desired monitoring state — user intent (Phase 13).

    Distinct from ``MonitoringStateRepository``, which holds *actual*
    worker/watch state. Written by the Desktop UI's Request* use cases,
    read by the Background Agent's ``MonitoringDesiredStateReconciler``.
    """

    def get_desired(
        self, *, account_id: str, provider: SourceType
    ) -> MonitoringDesiredStatus: ...
    def set_desired(
        self,
        *,
        account_id: str,
        provider: SourceType,
        desired: MonitoringDesiredStatus,
    ) -> None: ...


@runtime_checkable
class AppSettingsRepository(Protocol):
    """User-adjusted runtime settings shared between Desktop and Agent.

    A missing key means "use the configured (.env) default".
    """

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...


@runtime_checkable
class UnitOfWork(Protocol):
    """Transactional boundary owning repository instances."""

    topics: TopicRepository
    events: IntelligenceEventRepository
    profiles: AIProfileRepository
    analyses: AIAnalysisRepository
    attachments: AttachmentRepository
    notifications: NotificationRepository
    stories: StoryRepository
    monitoring_states: MonitoringStateRepository
    monitoring_control: MonitoringControlRepository
    app_settings: AppSettingsRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
