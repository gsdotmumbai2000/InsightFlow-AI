"""Domain ↔ SQLite row mappers."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from insightflow.application.exceptions import DataMappingError
from insightflow.domain import (
    AIAnalysis,
    AIAnalysisId,
    AIAnalysisStatus,
    AIOutputStyle,
    AIProfile,
    AIProfileId,
    Attachment,
    AttachmentDownloadStatus,
    AttachmentId,
    AttachmentProcessingStatus,
    Confidence,
    ContentHash,
    EventId,
    EventProcessingStatus,
    IntelligenceEvent,
    MarketImpact,
    MarketImpactDirection,
    MonitoringState,
    MonitoringStateId,
    MonitoringStatus,
    Notification,
    NotificationId,
    NotificationStatus,
    NotificationType,
    Priority,
    Sentiment,
    SourceConfiguration,
    SourceReference,
    SourceType,
    StorageReference,
    Story,
    StoryId,
    StoryStatus,
    Topic,
    TopicId,
    TopicStatus,
)
from insightflow.infrastructure.database.serialization import (
    bool_from_db,
    bool_to_db,
    datetime_from_db,
    datetime_to_db,
    json_dumps,
    json_loads,
)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def topic_to_row(topic: Topic) -> dict[str, Any]:
    return {
        "id": topic.id.value,
        "name": topic.name,
        "description": topic.description,
        "source_id": topic.source_configuration.source_id,
        "source_identifier": topic.source_configuration.source_identifier,
        "source_type": _enum_value(topic.source_configuration.source_type),
        "ai_profile_id": topic.ai_profile_id.value if topic.ai_profile_id else None,
        "notification_policy_json": (
            json_dumps({"ref": topic.notification_policy_ref})
            if topic.notification_policy_ref
            else None
        ),
        "status": _enum_value(topic.status),
        "enabled": bool_to_db(topic.enabled),
        "created_at": datetime_to_db(topic.created_at),
        "updated_at": datetime_to_db(topic.updated_at),
    }


def topic_from_row(row: Any) -> Topic:
    policy = json_loads(
        row["notification_policy_json"], field_name="notification_policy_json"
    )
    policy_ref = None
    if isinstance(policy, dict):
        ref = policy.get("ref")
        policy_ref = str(ref) if ref is not None else None
    return Topic(
        id=TopicId(row["id"]),
        name=row["name"],
        description=row["description"],
        status=TopicStatus(row["status"]),
        source_configuration=SourceConfiguration(
            source_type=SourceType(row["source_type"]),
            source_id=row["source_id"],
            source_identifier=row["source_identifier"],
        ),
        ai_profile_id=AIProfileId(row["ai_profile_id"])
        if row["ai_profile_id"]
        else None,
        notification_policy_ref=policy_ref,
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
    )


def event_to_row(event: IntelligenceEvent) -> dict[str, Any]:
    return {
        "id": event.id.value,
        "source_id": event.source.source_id,
        "topic_id": event.topic_id.value if event.topic_id else None,
        "external_id": event.source.external_id,
        "external_thread_id": event.source.thread_id,
        "occurred_at": datetime_to_db(event.source_published_at),
        "received_at": datetime_to_db(event.received_at),
        "title": event.title,
        "author": None,
        "content_text": event.normalized_content,
        "content_hash": event.content_hash.value if event.content_hash else None,
        "source_url": event.source.url,
        "source_type": _enum_value(event.source.source_type),
        "account_id": event.source.account_id,
        "metadata_json": json_dumps(event.metadata) if event.metadata else None,
        "status": _enum_value(event.status),
        "priority": _enum_value(event.priority) if event.priority else None,
        "story_id": event.story_id.value if event.story_id else None,
        "created_at": datetime_to_db(event.created_at),
        "updated_at": datetime_to_db(event.updated_at),
    }


def event_from_row(row: Any) -> IntelligenceEvent:
    metadata_raw = json_loads(row["metadata_json"], field_name="metadata_json")
    metadata: dict[str, str] = {}
    if metadata_raw is not None:
        if not isinstance(metadata_raw, dict):
            raise DataMappingError("metadata_json must be an object.")
        metadata = {str(k): str(v) for k, v in metadata_raw.items()}
    return IntelligenceEvent(
        id=EventId(row["id"]),
        topic_id=TopicId(row["topic_id"]) if row["topic_id"] else None,
        source=SourceReference(
            source_type=SourceType(row["source_type"]),
            source_id=row["source_id"],
            external_id=row["external_id"],
            thread_id=row["external_thread_id"],
            account_id=row["account_id"],
            url=row["source_url"],
        ),
        title=row["title"],
        normalized_content=row["content_text"],
        source_published_at=datetime_from_db(row["occurred_at"]),
        received_at=datetime_from_db(row["received_at"]),  # type: ignore[arg-type]
        status=EventProcessingStatus(row["status"]),
        priority=Priority(row["priority"]) if row["priority"] else None,
        content_hash=ContentHash(row["content_hash"]) if row["content_hash"] else None,
        story_id=StoryId(row["story_id"]) if row["story_id"] else None,
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
        metadata=metadata,
    )


def profile_to_rows(profile: AIProfile) -> tuple[dict[str, Any], dict[str, Any]]:
    version_id = str(uuid4())
    profile_row = {
        "id": profile.id.value,
        "name": profile.name,
        "description": profile.description,
        "active_version_id": version_id,
        "enabled": bool_to_db(profile.enabled),
        "created_at": datetime_to_db(profile.created_at),
        "updated_at": datetime_to_db(profile.updated_at),
    }
    version_row = {
        "id": version_id,
        "ai_profile_id": profile.id.value,
        "version_number": profile.version,
        "system_prompt": profile.instructions,
        "output_schema_json": json_dumps(
            {
                "schema_version": profile.output_schema_version,
                "output_style": profile.output_style.value,
            }
        ),
        "model_preferences_json": None,
        # updated_at: equals created_at for a new profile, and is when this
        # version was made for a revised one (see AIProfile.revise).
        "created_at": datetime_to_db(profile.updated_at),
        "created_by": None,
        "is_active": 1,
    }
    return profile_row, version_row


def profile_from_rows(profile_row: Any, version_row: Any) -> AIProfile:
    schema = json_loads(
        version_row["output_schema_json"], field_name="output_schema_json"
    )
    schema_version = "v1"
    output_style = AIOutputStyle.ANALYSIS  # versions saved before styles existed
    if isinstance(schema, dict):
        if schema.get("schema_version"):
            schema_version = str(schema["schema_version"])
        if schema.get("output_style"):
            try:
                output_style = AIOutputStyle(str(schema["output_style"]))
            except ValueError as exc:
                raise DataMappingError("Unknown AI profile output_style.") from exc
    return AIProfile(
        id=AIProfileId(profile_row["id"]),
        name=profile_row["name"],
        description=profile_row["description"],
        instructions=version_row["system_prompt"],
        version=int(version_row["version_number"]),
        enabled=bool_from_db(profile_row["enabled"]),
        output_schema_version=schema_version,
        created_at=datetime_from_db(profile_row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(profile_row["updated_at"]),  # type: ignore[arg-type]
        output_style=output_style,
    )


def _string_tuple_from_json(value: str | None, *, field_name: str) -> tuple[str, ...]:
    loaded = json_loads(value, field_name=field_name)
    if loaded is None:
        return ()
    if not isinstance(loaded, list):
        raise DataMappingError(f"{field_name} must be a JSON array.")
    return tuple(str(item) for item in loaded)


def _market_impact_to_json(impact: MarketImpact | None) -> str | None:
    if impact is None:
        return None
    return json_dumps(
        {
            "relevance": impact.relevance,
            "direction": impact.direction.value,
            "affected_assets": list(impact.affected_assets),
            "reasoning": impact.reasoning,
            "confidence": impact.confidence.value,
        }
    )


def _market_impact_from_json(value: str | None) -> MarketImpact | None:
    loaded = json_loads(value, field_name="market_impact_json")
    if loaded is None:
        return None
    if not isinstance(loaded, dict):
        raise DataMappingError("market_impact_json must be an object.")
    return MarketImpact(
        relevance=str(loaded["relevance"]),
        direction=MarketImpactDirection(str(loaded["direction"])),
        affected_assets=tuple(str(item) for item in loaded.get("affected_assets", [])),
        reasoning=str(loaded["reasoning"]),
        confidence=Confidence(float(loaded["confidence"])),
    )


def analysis_to_row(analysis: AIAnalysis, *, profile_version_id: str) -> dict[str, Any]:
    return {
        "id": analysis.id.value,
        "event_id": analysis.event_id.value,
        "ai_profile_id": analysis.profile_id.value,
        "ai_profile_version_id": profile_version_id,
        "provider": analysis.provider,
        "model": analysis.model,
        "headline": None,
        "summary": analysis.summary,
        "why_it_matters": analysis.why_it_matters,
        "facts_json": json_dumps(list(analysis.key_facts)),
        "what_to_watch_json": json_dumps(list(analysis.what_to_watch)),
        "entities_json": json_dumps(list(analysis.entities)),
        "importance": None,
        "priority": _enum_value(analysis.priority) if analysis.priority else None,
        "confidence": analysis.confidence.value if analysis.confidence else None,
        "sentiment": _enum_value(analysis.sentiment) if analysis.sentiment else None,
        "market_impact_json": _market_impact_to_json(analysis.market_impact),
        "status": _enum_value(analysis.status),
        "failure_reason": analysis.failure_reason,
        "latency_ms": analysis.latency_ms,
        "created_at": datetime_to_db(analysis.created_at),
        "updated_at": datetime_to_db(analysis.updated_at),
    }


def analysis_from_row(row: Any) -> AIAnalysis:
    confidence = None
    if row["confidence"] is not None:
        confidence = Confidence(float(row["confidence"]))
    return AIAnalysis(
        id=AIAnalysisId(row["id"]),
        event_id=EventId(row["event_id"]),
        profile_id=AIProfileId(row["ai_profile_id"]),
        profile_version=_profile_version_number_placeholder(row),
        provider=row["provider"],
        model=row["model"],
        summary=row["summary"],
        why_it_matters=row["why_it_matters"],
        key_facts=_string_tuple_from_json(row["facts_json"], field_name="facts_json"),
        what_to_watch=_string_tuple_from_json(
            row["what_to_watch_json"], field_name="what_to_watch_json"
        ),
        market_impact=_market_impact_from_json(row["market_impact_json"]),
        entities=_string_tuple_from_json(
            row["entities_json"], field_name="entities_json"
        ),
        sentiment=Sentiment(row["sentiment"]) if row["sentiment"] else None,
        confidence=confidence,
        status=AIAnalysisStatus(row["status"]),
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
        priority=Priority(row["priority"]) if row["priority"] else None,
        latency_ms=row["latency_ms"],
        failure_reason=row["failure_reason"],
        generated_content=(
            # keys(): `in` on a sqlite3.Row tests values, not column names.
            row["generated_content"]
            if "generated_content" in row.keys()  # noqa: SIM118
            else None
        ),
    )


def _profile_version_number_placeholder(row: Any) -> int:
    # Repositories overwrite this when joining version rows.
    if "version_number" in row and row["version_number"] is not None:
        return int(row["version_number"])
    return 1


def attachment_to_row(attachment: Attachment) -> dict[str, Any]:
    return {
        "id": attachment.id.value,
        "event_id": attachment.event_id.value,
        "external_id": attachment.external_id,
        "filename": attachment.filename,
        "mime_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "download_status": _enum_value(attachment.download_status),
        "processing_status": _enum_value(attachment.processing_status),
        "storage_reference": (
            attachment.storage_reference.value if attachment.storage_reference else None
        ),
        "created_at": datetime_to_db(attachment.created_at),
        "updated_at": datetime_to_db(attachment.updated_at),
    }


def attachment_from_row(row: Any) -> Attachment:
    return Attachment(
        id=AttachmentId(row["id"]),
        event_id=EventId(row["event_id"]),
        filename=row["filename"],
        content_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        storage_reference=(
            StorageReference(row["storage_reference"])
            if row["storage_reference"]
            else None
        ),
        download_status=AttachmentDownloadStatus(row["download_status"]),
        processing_status=AttachmentProcessingStatus(row["processing_status"]),
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
        external_id=row["external_id"],
    )


def notification_to_row(notification: Notification) -> dict[str, Any]:
    return {
        "id": notification.id.value,
        "event_id": notification.event_id.value,
        "topic_id": notification.topic_id.value if notification.topic_id else None,
        "priority": _enum_value(notification.priority),
        "notification_type": _enum_value(notification.notification_type),
        "title": notification.title,
        "summary": notification.summary,
        "status": _enum_value(notification.status),
        "provider": "windows",
        "created_at": datetime_to_db(notification.created_at),
        "updated_at": datetime_to_db(notification.updated_at),
        "displayed_at": datetime_to_db(notification.displayed_at),
        "dismissed_at": datetime_to_db(notification.dismissed_at),
        "failure_message": notification.failure_message,
    }


def notification_from_row(row: Any) -> Notification:
    return Notification(
        id=NotificationId(row["id"]),
        event_id=EventId(row["event_id"]),
        topic_id=TopicId(row["topic_id"]) if row["topic_id"] else None,
        priority=Priority(row["priority"]),
        notification_type=NotificationType(row["notification_type"]),
        title=row["title"],
        summary=row["summary"],
        status=NotificationStatus(row["status"]),
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
        displayed_at=datetime_from_db(row["displayed_at"]),
        dismissed_at=datetime_from_db(row["dismissed_at"]),
        failure_message=row["failure_message"],
    )


def story_to_row(story: Story) -> dict[str, Any]:
    return {
        "id": story.id.value,
        "topic_id": story.topic_id.value if story.topic_id else None,
        "title": story.title,
        "summary": story.summary,
        "status": _enum_value(story.status),
        "first_event_at": datetime_to_db(story.first_event_at),
        "last_event_at": datetime_to_db(story.last_event_at),
        "created_at": datetime_to_db(story.created_at),
        "updated_at": datetime_to_db(story.updated_at),
    }


def monitoring_state_to_row(state: MonitoringState) -> dict[str, Any]:
    return {
        "id": state.id.value,
        "account_id": state.account_id,
        "provider": _enum_value(state.provider),
        "pubsub_project_id": state.pubsub_project_id,
        "pubsub_topic": state.pubsub_topic,
        "pubsub_subscription": state.pubsub_subscription,
        "current_history_id": state.current_history_id,
        "watch_expiration": datetime_to_db(state.watch_expiration),
        "status": _enum_value(state.status),
        "last_notification_at": datetime_to_db(state.last_notification_at),
        "last_sync_at": datetime_to_db(state.last_sync_at),
        "last_error": state.last_error,
        "created_at": datetime_to_db(state.created_at),
        "updated_at": datetime_to_db(state.updated_at),
    }


def monitoring_state_from_row(row: Any) -> MonitoringState:
    return MonitoringState(
        id=MonitoringStateId(row["id"]),
        account_id=row["account_id"],
        provider=SourceType(row["provider"]),
        pubsub_project_id=row["pubsub_project_id"],
        pubsub_topic=row["pubsub_topic"],
        pubsub_subscription=row["pubsub_subscription"],
        current_history_id=row["current_history_id"],
        watch_expiration=datetime_from_db(row["watch_expiration"]),
        status=MonitoringStatus(row["status"]),
        last_notification_at=datetime_from_db(row["last_notification_at"]),
        last_sync_at=datetime_from_db(row["last_sync_at"]),
        last_error=row["last_error"],
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
    )


def story_from_row(row: Any, event_ids: tuple[EventId, ...]) -> Story:
    return Story(
        id=StoryId(row["id"]),
        topic_id=TopicId(row["topic_id"]) if row["topic_id"] else None,
        title=row["title"],
        summary=row["summary"],
        status=StoryStatus(row["status"]),
        event_ids=event_ids,
        first_event_at=datetime_from_db(row["first_event_at"]),
        last_event_at=datetime_from_db(row["last_event_at"]),
        created_at=datetime_from_db(row["created_at"]),  # type: ignore[arg-type]
        updated_at=datetime_from_db(row["updated_at"]),  # type: ignore[arg-type]
    )
