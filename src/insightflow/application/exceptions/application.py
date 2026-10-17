"""Application-layer business exceptions."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base application error exposed to callers (e.g. presentation)."""


class ApplicationValidationError(ApplicationError):
    """Raised when use-case input is invalid."""


class NotFoundError(ApplicationError):
    """Raised when a requested entity does not exist."""


class TopicNotFoundError(NotFoundError):
    """Topic lookup failed."""


class EventNotFoundError(NotFoundError):
    """Intelligence event lookup failed."""


class AIAnalysisNotFoundError(NotFoundError):
    """AI analysis lookup failed."""


class NotificationNotFoundError(NotFoundError):
    """Notification lookup failed."""


class AttachmentNotFoundError(NotFoundError):
    """Attachment lookup failed."""


class StoryNotFoundError(NotFoundError):
    """Story lookup failed."""


class AIProfileNotFoundError(NotFoundError):
    """AI profile lookup failed."""


class AIProfileNotConfiguredError(ApplicationError):
    """No AI profile is configured for the event's topic (or none was given)."""


class DuplicateTopicError(ApplicationError):
    """Raised when creating a topic that violates uniqueness rules."""


class DuplicateEventError(ApplicationError):
    """Raised when creating an event that violates source-identity uniqueness."""


class InvalidOperationError(ApplicationError):
    """Raised when a requested state transition or operation is not allowed."""
