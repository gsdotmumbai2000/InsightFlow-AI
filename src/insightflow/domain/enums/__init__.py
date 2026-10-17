"""Domain enumerations for statuses and classifications."""

from __future__ import annotations

from enum import StrEnum


class TopicStatus(StrEnum):
    """Lifecycle status for a monitoring topic."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    PAUSED = "PAUSED"


class EventProcessingStatus(StrEnum):
    """Processing lifecycle for an intelligence event."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    NORMALIZED = "NORMALIZED"
    TOPIC_RESOLVED = "TOPIC_RESOLVED"
    DEDUPLICATING = "DEDUPLICATING"
    AI_PENDING = "AI_PENDING"
    AI_PROCESSING = "AI_PROCESSING"
    AI_COMPLETED = "AI_COMPLETED"
    PERSISTING = "PERSISTING"
    NOTIFICATION_PENDING = "NOTIFICATION_PENDING"
    COMPLETED = "COMPLETED"
    RETRY_PENDING = "RETRY_PENDING"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
    IGNORED = "IGNORED"


class Priority(StrEnum):
    """Business priority classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AIAnalysisStatus(StrEnum):
    """Lifecycle status for an AI analysis result."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Sentiment(StrEnum):
    """Optional sentiment classification (not market direction)."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AIOutputStyle(StrEnum):
    """What an AI profile asks the model to produce.

    ANALYSIS: the structured analysis (summary, key facts, market impact...).
    CUSTOM_TEXT: whatever the profile's instructions ask for (e.g. a news
    script), returned as free text, plus a short summary for lists.
    """

    ANALYSIS = "ANALYSIS"
    CUSTOM_TEXT = "CUSTOM_TEXT"


class MarketImpactDirection(StrEnum):
    """Directional market interpretation — not a guaranteed prediction."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    MIXED = "MIXED"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NotificationStatus(StrEnum):
    """Lifecycle status for a user notification."""

    PENDING = "PENDING"
    DISPLAYED = "DISPLAYED"
    DISMISSED = "DISMISSED"
    OPENED = "OPENED"
    SUPPRESSED = "SUPPRESSED"
    FAILED = "FAILED"


class NotificationType(StrEnum):
    """High-level notification category."""

    EVENT_ALERT = "EVENT_ALERT"
    SYSTEM = "SYSTEM"


class AttachmentDownloadStatus(StrEnum):
    """Download lifecycle for an attachment."""

    NOT_REQUESTED = "NOT_REQUESTED"
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    FAILED = "FAILED"


class AttachmentProcessingStatus(StrEnum):
    """Processing lifecycle for an attachment."""

    NOT_REQUESTED = "NOT_REQUESTED"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


class StoryStatus(StrEnum):
    """Lifecycle status for a story grouping."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class SourceType(StrEnum):
    """Provider-neutral source type.

    Extensible over time; domain code must not assume Gmail is the only source.
    """

    GMAIL = "GMAIL"
    GENERIC = "GENERIC"


class MonitoringStatus(StrEnum):
    """Lifecycle status for real-time source monitoring (Phase 10)."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class MonitoringDesiredStatus(StrEnum):
    """Persisted user intent for monitoring, independent of actual worker
    state (Phase 13). Written by the Desktop UI, read and reconciled by the
    Background Agent — see ``application.services.monitoring_reconciler``.
    """

    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
