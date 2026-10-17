"""Map domain entities to application DTOs."""

from __future__ import annotations

from insightflow.application.dto.models import (
    AIAnalysisDto,
    AIProfileDto,
    AttachmentDto,
    IntelligenceEventDto,
    MarketImpactDto,
    NotificationDto,
    SourceConfigurationDto,
    SourceReferenceDto,
    StoryDto,
    TopicDto,
)
from insightflow.domain import (
    AIAnalysis,
    AIProfile,
    Attachment,
    IntelligenceEvent,
    MarketImpact,
    Notification,
    SourceConfiguration,
    SourceReference,
    Story,
    Topic,
)


def source_configuration_to_dto(value: SourceConfiguration) -> SourceConfigurationDto:
    return SourceConfigurationDto(
        source_type=value.source_type.value,
        source_id=value.source_id,
        source_identifier=value.source_identifier,
    )


def source_reference_to_dto(value: SourceReference) -> SourceReferenceDto:
    return SourceReferenceDto(
        source_type=value.source_type.value,
        source_id=value.source_id,
        external_id=value.external_id,
        thread_id=value.thread_id,
        account_id=value.account_id,
        url=value.url,
    )


def market_impact_to_dto(value: MarketImpact) -> MarketImpactDto:
    return MarketImpactDto(
        relevance=value.relevance,
        direction=value.direction.value,
        affected_assets=value.affected_assets,
        reasoning=value.reasoning,
        confidence=value.confidence.value,
    )


def profile_to_dto(profile: AIProfile) -> AIProfileDto:
    return AIProfileDto(
        id=profile.id.value,
        name=profile.name,
        description=profile.description,
        instructions=profile.instructions,
        version=profile.version,
        enabled=profile.enabled,
        output_schema_version=profile.output_schema_version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        output_style=profile.output_style.value,
    )


def topic_to_dto(topic: Topic) -> TopicDto:
    return TopicDto(
        id=topic.id.value,
        name=topic.name,
        description=topic.description,
        status=topic.status.value,
        enabled=topic.enabled,
        source=source_configuration_to_dto(topic.source_configuration),
        ai_profile_id=topic.ai_profile_id.value if topic.ai_profile_id else None,
        notification_policy_ref=topic.notification_policy_ref,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
    )


def event_to_dto(event: IntelligenceEvent) -> IntelligenceEventDto:
    return IntelligenceEventDto(
        id=event.id.value,
        topic_id=event.topic_id.value if event.topic_id else None,
        source=source_reference_to_dto(event.source),
        title=event.title,
        normalized_content=event.normalized_content,
        source_published_at=event.source_published_at,
        received_at=event.received_at,
        status=event.status.value,
        priority=event.priority.value if event.priority else None,
        content_hash=event.content_hash.value if event.content_hash else None,
        story_id=event.story_id.value if event.story_id else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def analysis_to_dto(analysis: AIAnalysis) -> AIAnalysisDto:
    return AIAnalysisDto(
        id=analysis.id.value,
        event_id=analysis.event_id.value,
        profile_id=analysis.profile_id.value,
        profile_version=analysis.profile_version,
        provider=analysis.provider,
        model=analysis.model,
        summary=analysis.summary,
        why_it_matters=analysis.why_it_matters,
        key_facts=analysis.key_facts,
        what_to_watch=analysis.what_to_watch,
        entities=analysis.entities,
        sentiment=analysis.sentiment.value if analysis.sentiment else None,
        confidence=analysis.confidence.value if analysis.confidence else None,
        market_impact=(
            market_impact_to_dto(analysis.market_impact)
            if analysis.market_impact
            else None
        ),
        status=analysis.status.value,
        priority=analysis.priority.value if analysis.priority else None,
        latency_ms=analysis.latency_ms,
        failure_reason=analysis.failure_reason,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
        generated_content=analysis.generated_content,
    )


def notification_to_dto(notification: Notification) -> NotificationDto:
    return NotificationDto(
        id=notification.id.value,
        event_id=notification.event_id.value,
        topic_id=notification.topic_id.value if notification.topic_id else None,
        priority=notification.priority.value,
        notification_type=notification.notification_type.value,
        title=notification.title,
        summary=notification.summary,
        status=notification.status.value,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
        displayed_at=notification.displayed_at,
        dismissed_at=notification.dismissed_at,
        failure_message=notification.failure_message,
    )


def attachment_to_dto(attachment: Attachment) -> AttachmentDto:
    return AttachmentDto(
        id=attachment.id.value,
        event_id=attachment.event_id.value,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        storage_reference=(
            attachment.storage_reference.value if attachment.storage_reference else None
        ),
        download_status=attachment.download_status.value,
        processing_status=attachment.processing_status.value,
        external_id=attachment.external_id,
        created_at=attachment.created_at,
        updated_at=attachment.updated_at,
    )


def story_to_dto(story: Story) -> StoryDto:
    return StoryDto(
        id=story.id.value,
        topic_id=story.topic_id.value if story.topic_id else None,
        title=story.title,
        summary=story.summary,
        status=story.status.value,
        event_ids=tuple(event_id.value for event_id in story.event_ids),
        first_event_at=story.first_event_at,
        last_event_at=story.last_event_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )
