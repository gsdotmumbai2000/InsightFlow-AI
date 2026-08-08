"""Topic entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from insightflow.domain.enums import TopicStatus
from insightflow.domain.exceptions import InvalidStateTransitionError
from insightflow.domain.value_objects import AIProfileId, SourceConfiguration, TopicId
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class Topic:
    """Something the user wants to monitor."""

    id: TopicId
    name: str
    description: str | None
    status: TopicStatus
    source_configuration: SourceConfiguration
    ai_profile_id: AIProfileId | None
    created_at: datetime
    updated_at: datetime
    notification_policy_ref: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "Topic.name")
        if self.description is not None:
            self.description = require_non_empty(self.description, "Topic.description")
        self.created_at = require_aware_utc(self.created_at, "Topic.created_at")
        self.updated_at = require_aware_utc(self.updated_at, "Topic.updated_at")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        source_configuration: SourceConfiguration,
        description: str | None = None,
        ai_profile_id: AIProfileId | None = None,
        notification_policy_ref: str | None = None,
        topic_id: TopicId | None = None,
        created_at: datetime | None = None,
    ) -> Topic:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=topic_id or TopicId.generate(),
            name=name,
            description=description,
            status=TopicStatus.ENABLED,
            source_configuration=source_configuration,
            ai_profile_id=ai_profile_id,
            notification_policy_ref=notification_policy_ref,
            created_at=timestamp,
            updated_at=timestamp,
        )

    @property
    def enabled(self) -> bool:
        return self.status is TopicStatus.ENABLED

    def enable(self, *, at: datetime | None = None) -> None:
        if self.status is TopicStatus.ENABLED:
            return
        self.status = TopicStatus.ENABLED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def disable(self, *, at: datetime | None = None) -> None:
        if self.status is TopicStatus.DISABLED:
            return
        self.status = TopicStatus.DISABLED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def pause(self, *, at: datetime | None = None) -> None:
        if self.status is TopicStatus.DISABLED:
            raise InvalidStateTransitionError(
                "Cannot pause a disabled topic; enable it first."
            )
        if self.status is TopicStatus.PAUSED:
            return
        self.status = TopicStatus.PAUSED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def resume(self, *, at: datetime | None = None) -> None:
        if self.status is TopicStatus.DISABLED:
            raise InvalidStateTransitionError(
                "Cannot resume a disabled topic; enable it instead."
            )
        if self.status is TopicStatus.ENABLED:
            return
        self.status = TopicStatus.ENABLED
        self.updated_at = require_aware_utc(at or utc_now(), "at")
