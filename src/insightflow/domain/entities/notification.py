"""Notification entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from insightflow.domain.enums import NotificationStatus, NotificationType, Priority
from insightflow.domain.exceptions import InvalidStateTransitionError
from insightflow.domain.value_objects import EventId, NotificationId, TopicId
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class Notification:
    """Application decision/output to notify the user (UI-agnostic)."""

    id: NotificationId
    event_id: EventId
    topic_id: TopicId | None
    priority: Priority
    notification_type: NotificationType
    title: str
    summary: str | None
    status: NotificationStatus
    created_at: datetime
    updated_at: datetime
    displayed_at: datetime | None = None
    dismissed_at: datetime | None = None
    failure_message: str | None = None

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, "title")
        if self.summary is not None:
            self.summary = require_non_empty(self.summary, "summary")
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")
        if self.displayed_at is not None:
            self.displayed_at = require_aware_utc(self.displayed_at, "displayed_at")
        if self.dismissed_at is not None:
            self.dismissed_at = require_aware_utc(self.dismissed_at, "dismissed_at")

    @classmethod
    def create(
        cls,
        *,
        event_id: EventId,
        priority: Priority,
        title: str,
        summary: str | None = None,
        topic_id: TopicId | None = None,
        notification_type: NotificationType = NotificationType.EVENT_ALERT,
        notification_id: NotificationId | None = None,
        created_at: datetime | None = None,
    ) -> Notification:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=notification_id or NotificationId.generate(),
            event_id=event_id,
            topic_id=topic_id,
            priority=priority,
            notification_type=notification_type,
            title=title,
            summary=summary,
            status=NotificationStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def mark_displayed(self, *, at: datetime | None = None) -> None:
        if self.status in {
            NotificationStatus.DISMISSED,
            NotificationStatus.FAILED,
            NotificationStatus.SUPPRESSED,
        }:
            raise InvalidStateTransitionError(
                f"Cannot mark_displayed from status {self.status.value}."
            )
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.status = NotificationStatus.DISPLAYED
        self.displayed_at = timestamp
        self.updated_at = timestamp
        self.failure_message = None

    def mark_dismissed(self, *, at: datetime | None = None) -> None:
        if self.status not in {
            NotificationStatus.DISPLAYED,
            NotificationStatus.OPENED,
            NotificationStatus.PENDING,
        }:
            raise InvalidStateTransitionError(
                f"Cannot mark_dismissed from status {self.status.value}."
            )
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.status = NotificationStatus.DISMISSED
        self.dismissed_at = timestamp
        self.updated_at = timestamp

    def mark_failed(self, *, reason: str, at: datetime | None = None) -> None:
        if self.status in {
            NotificationStatus.DISMISSED,
            NotificationStatus.OPENED,
        }:
            raise InvalidStateTransitionError(
                f"Cannot mark_failed from status {self.status.value}."
            )
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.status = NotificationStatus.FAILED
        self.failure_message = require_non_empty(reason, "reason")
        self.updated_at = timestamp
