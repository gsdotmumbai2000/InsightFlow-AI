"""Application input and output DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceConfigurationDto:
    source_type: str
    source_id: str
    source_identifier: str


@dataclass(frozen=True, slots=True)
class SourceReferenceDto:
    source_type: str
    source_id: str
    external_id: str
    thread_id: str | None = None
    account_id: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class MarketImpactDto:
    relevance: str
    direction: str
    affected_assets: tuple[str, ...]
    reasoning: str
    confidence: float


@dataclass(frozen=True, slots=True)
class AIProfileDto:
    id: str
    name: str
    description: str | None
    instructions: str
    version: int
    enabled: bool
    output_schema_version: str
    created_at: datetime
    updated_at: datetime
    output_style: str = "ANALYSIS"  # AIOutputStyle value


@dataclass(frozen=True, slots=True)
class CreateAIProfileRequest:
    name: str
    instructions: str
    output_schema_version: str = "v1"
    description: str | None = None
    output_style: str = "ANALYSIS"  # AIOutputStyle value


@dataclass(frozen=True, slots=True)
class UpdateAIProfileRequest:
    profile_id: str
    name: str
    instructions: str
    description: str | None = None
    output_style: str | None = None  # None keeps the current style


@dataclass(frozen=True, slots=True)
class TopicDto:
    id: str
    name: str
    description: str | None
    status: str
    enabled: bool
    source: SourceConfigurationDto
    ai_profile_id: str | None
    notification_policy_ref: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CreateTopicRequest:
    name: str
    source_type: str
    source_id: str
    source_identifier: str
    description: str | None = None
    ai_profile_id: str | None = None
    notification_policy_ref: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTopicRequest:
    topic_id: str
    name: str | None = None
    description: str | None = None
    ai_profile_id: str | None = None
    notification_policy_ref: str | None = None
    clear_ai_profile: bool = False
    clear_notification_policy: bool = False


@dataclass(frozen=True, slots=True)
class IntelligenceEventDto:
    id: str
    topic_id: str | None
    source: SourceReferenceDto
    title: str | None
    normalized_content: str | None
    source_published_at: datetime | None
    received_at: datetime
    status: str
    priority: str | None
    content_hash: str | None
    story_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CreateIntelligenceEventRequest:
    source_type: str
    source_id: str
    external_id: str
    topic_id: str | None = None
    thread_id: str | None = None
    account_id: str | None = None
    url: str | None = None
    title: str | None = None
    normalized_content: str | None = None
    source_published_at: datetime | None = None
    received_at: datetime | None = None
    priority: str | None = None
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class AIAnalysisDto:
    id: str
    event_id: str
    profile_id: str
    profile_version: int
    provider: str
    model: str
    summary: str
    why_it_matters: str | None
    key_facts: tuple[str, ...]
    what_to_watch: tuple[str, ...]
    entities: tuple[str, ...]
    sentiment: str | None
    confidence: float | None
    market_impact: MarketImpactDto | None
    status: str
    priority: str | None
    latency_ms: int | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    generated_content: str | None = None


@dataclass(frozen=True, slots=True)
class ReprocessAIRequest:
    event_id: str
    ai_profile_id: str | None = None
    profile_version: int | None = None


@dataclass(frozen=True, slots=True)
class ReprocessAIResult:
    """Application intent for a future AI worker (no provider call)."""

    event_id: str
    status: str
    ai_profile_id: str | None
    profile_version: int | None
    requested_at: datetime
    message: str


@dataclass(frozen=True, slots=True)
class NotificationDto:
    id: str
    event_id: str
    topic_id: str | None
    priority: str
    notification_type: str
    title: str
    summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    displayed_at: datetime | None
    dismissed_at: datetime | None
    failure_message: str | None


@dataclass(frozen=True, slots=True)
class AttachmentDto:
    id: str
    event_id: str
    filename: str
    content_type: str | None
    size_bytes: int | None
    storage_reference: str | None
    download_status: str
    processing_status: str
    external_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoryDto:
    id: str
    topic_id: str | None
    title: str
    summary: str | None
    status: str
    event_ids: tuple[str, ...]
    first_event_at: datetime | None
    last_event_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardSummaryDto:
    enabled_topic_count: int
    total_topic_count: int
    recent_event_count: int
    high_priority_event_count: int
    unprocessed_event_count: int
    pending_notification_count: int
    completed_analysis_recent_count: int
    monitoring_status: str | None
    recent_events: tuple[IntelligenceEventDto, ...]
    recent_notifications: tuple[NotificationDto, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)
