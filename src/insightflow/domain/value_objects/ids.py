"""Typed immutable domain identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from insightflow.domain.value_objects._guards import require_non_empty


def _new_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class TopicId:
    """Unique identifier for a Topic."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "TopicId"))

    @classmethod
    def generate(cls) -> TopicId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class EventId:
    """Unique identifier for an IntelligenceEvent."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "EventId"))

    @classmethod
    def generate(cls) -> EventId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class AIProfileId:
    """Unique identifier for an AIProfile."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "AIProfileId"))

    @classmethod
    def generate(cls) -> AIProfileId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class AIAnalysisId:
    """Unique identifier for an AIAnalysis."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "AIAnalysisId"))

    @classmethod
    def generate(cls) -> AIAnalysisId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class AttachmentId:
    """Unique identifier for an Attachment."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "AttachmentId"))

    @classmethod
    def generate(cls) -> AttachmentId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class NotificationId:
    """Unique identifier for a Notification."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", require_non_empty(self.value, "NotificationId")
        )

    @classmethod
    def generate(cls) -> NotificationId:
        return cls(_new_id())


@dataclass(frozen=True, slots=True)
class StoryId:
    """Unique identifier for a Story."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "StoryId"))

    @classmethod
    def generate(cls) -> StoryId:
        return cls(_new_id())
