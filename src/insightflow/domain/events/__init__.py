"""Minimal domain event definitions (no bus implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from insightflow.domain.value_objects import (
    AIAnalysisId,
    EventId,
    NotificationId,
    TopicId,
)
from insightflow.domain.value_objects._guards import require_aware_utc


@dataclass(frozen=True, slots=True)
class IntelligenceEventCreated:
    """Raised conceptually when a new intelligence event enters the domain."""

    event_id: EventId
    topic_id: TopicId | None
    occurred_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "occurred_at",
            require_aware_utc(self.occurred_at, "occurred_at"),
        )


@dataclass(frozen=True, slots=True)
class AIAnalysisCompleted:
    """Raised conceptually when an AI analysis is completed successfully."""

    analysis_id: AIAnalysisId
    event_id: EventId
    occurred_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "occurred_at",
            require_aware_utc(self.occurred_at, "occurred_at"),
        )


@dataclass(frozen=True, slots=True)
class NotificationRequested:
    """Raised conceptually when a notification should be delivered."""

    notification_id: NotificationId
    event_id: EventId
    occurred_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "occurred_at",
            require_aware_utc(self.occurred_at, "occurred_at"),
        )
