"""SQLite repository integration and round-trip tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from insightflow.application.exceptions import DuplicateEntityError, PersistenceError
from insightflow.domain import (
    AIAnalysis,
    AIOutputStyle,
    AIProfile,
    Attachment,
    Confidence,
    ContentHash,
    EventProcessingStatus,
    IntelligenceEvent,
    MarketImpact,
    MarketImpactDirection,
    MonitoringState,
    Notification,
    Priority,
    Sentiment,
    SourceConfiguration,
    SourceReference,
    SourceType,
    Story,
    Topic,
)
from insightflow.infrastructure.database.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "insightflow.db"


def _source_config() -> SourceConfiguration:
    return SourceConfiguration(
        source_type=SourceType.GMAIL,
        source_id="gmail-account-1",
        source_identifier="Label_42",
    )


def _source_ref() -> SourceReference:
    return SourceReference(
        source_type=SourceType.GMAIL,
        source_id="gmail-account-1",
        external_id="msg-100",
        thread_id="thread-9",
        url="https://example.test/msg",
    )


def test_topic_crud_and_round_trip(db_path: Path) -> None:
    profile = AIProfile.create(
        name="General",
        instructions="Summarize",
        output_schema_version="v1",
    )
    topic = Topic.create(
        name="Watchlist",
        source_configuration=_source_config(),
        description="Demo",
        ai_profile_id=profile.id,
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.profiles.add(profile)
        uow.topics.add(topic)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded = uow.topics.get(topic.id)
        assert loaded is not None
        assert loaded.name == "Watchlist"
        assert loaded.source_configuration.source_identifier == "Label_42"
        assert loaded.ai_profile_id == profile.id
        loaded.disable(at=datetime(2026, 1, 2, tzinfo=UTC))
        uow.topics.update(loaded)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        updated = uow.topics.get(topic.id)
        assert updated is not None
        assert updated.enabled is False
        assert uow.topics.list_enabled() == []
        assert (
            uow.topics.find_by_source_identifier(
                source_id="gmail-account-1",
                source_identifier="Label_42",
            )
            is not None
        )


def test_event_duplicate_and_queries(db_path: Path) -> None:
    event = IntelligenceEvent.create(
        source=_source_ref(),
        title="Headline",
        normalized_content="Body",
        content_hash=ContentHash("abc123"),
        priority=Priority.HIGH,
        received_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.events.add(event)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        with pytest.raises(DuplicateEntityError):
            uow.events.add(event)
        uow.rollback()

    with SQLiteUnitOfWork(db_path) as uow:
        found = uow.events.find_by_external_id(
            source_id="gmail-account-1", external_id="msg-100"
        )
        assert found is not None
        assert found.title == "Headline"
        found.mark_processing()
        uow.events.update(found)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded = uow.events.get(event.id)
        assert loaded is not None
        assert loaded.status is EventProcessingStatus.AI_PROCESSING
        assert uow.events.list_recent(limit=10)
        processing = uow.events.list_by_status(EventProcessingStatus.AI_PROCESSING)
        assert [item.id for item in processing] == [event.id]
        assert uow.events.list_by_status(EventProcessingStatus.COMPLETED) == []


def test_transaction_rollback(db_path: Path) -> None:
    topic = Topic.create(name="Temp", source_configuration=_source_config())
    with SQLiteUnitOfWork(db_path) as uow:
        uow.topics.add(topic)
        uow.rollback()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.topics.get(topic.id) is None


def test_analysis_attachment_notification_story_round_trips(db_path: Path) -> None:
    profile = AIProfile.create(
        name="General",
        instructions="Analyze carefully",
        output_schema_version="v1",
        version=1,
    )
    topic = Topic.create(
        name="Topic A",
        source_configuration=_source_config(),
        ai_profile_id=profile.id,
    )
    event = IntelligenceEvent.create(
        source=_source_ref(),
        topic_id=topic.id,
        title="Event",
        normalized_content="Content",
    )
    analysis = AIAnalysis.create(
        event_id=event.id,
        profile_id=profile.id,
        profile_version=1,
        provider="test",
        model="test-model",
        summary="Summary",
        why_it_matters="Interpretation",
        key_facts=("Fact 1", "Fact 2"),
        what_to_watch=("Signal",),
        entities=("Entity",),
        sentiment=Sentiment.NEUTRAL,
        confidence=Confidence(0.75),
        market_impact=MarketImpact(
            relevance="Moderate",
            direction=MarketImpactDirection.UNCERTAIN,
            affected_assets=("equities",),
            reasoning="Mixed",
            confidence=Confidence(0.4),
        ),
        priority=Priority.MEDIUM,
    )
    analysis.mark_completed()
    attachment = Attachment.create(
        event_id=event.id,
        filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )
    notification = Notification.create(
        event_id=event.id,
        topic_id=topic.id,
        priority=Priority.HIGH,
        title="Notify",
        summary="Body",
    )
    story = Story.create(title="Story", topic_id=topic.id)

    with SQLiteUnitOfWork(db_path) as uow:
        uow.profiles.add(profile)
        uow.topics.add(topic)
        uow.events.add(event)
        uow.analyses.add(analysis)
        uow.attachments.add(attachment)
        uow.notifications.add(notification)
        uow.stories.add(story)
        story.add_event(event.id)
        uow.stories.update(story)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded_analysis = uow.analyses.find_latest_by_event(event.id)
        assert loaded_analysis is not None
        assert loaded_analysis.summary == "Summary"
        assert loaded_analysis.key_facts == ("Fact 1", "Fact 2")
        assert loaded_analysis.market_impact is not None
        assert loaded_analysis.confidence is not None
        assert loaded_analysis.confidence.value == 0.75

        loaded_attachment = uow.attachments.get(attachment.id)
        assert loaded_attachment is not None
        assert loaded_attachment.filename == "doc.pdf"

        pending = uow.notifications.list_pending()
        assert len(pending) == 1
        pending[0].mark_displayed(at=datetime(2026, 1, 3, tzinfo=UTC))
        uow.notifications.update(pending[0])
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        note = uow.notifications.get(notification.id)
        assert note is not None
        assert note.displayed_at is not None
        loaded_story = uow.stories.get(story.id)
        assert loaded_story is not None
        assert event.id in loaded_story.event_ids


def test_monitoring_state_crud_and_round_trip(db_path: Path) -> None:
    state = MonitoringState.create(
        account_id="user@example.com",
        provider=SourceType.GMAIL,
        pubsub_project_id="proj-1",
        pubsub_topic="gmail-topic",
        pubsub_subscription="gmail-sub",
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.monitoring_states.add(state)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded = uow.monitoring_states.get(state.id)
        assert loaded is not None
        assert loaded.account_id == "user@example.com"
        assert loaded.provider is SourceType.GMAIL
        assert loaded.pubsub_topic == "gmail-topic"
        assert loaded.current_history_id is None
        assert loaded.watch_expiration is None
        assert loaded.status.value == "NOT_CONFIGURED"

        by_account = uow.monitoring_states.get_by_account(
            account_id="user@example.com", provider=SourceType.GMAIL
        )
        assert by_account is not None
        assert by_account.id == state.id

        loaded.update_watch(
            history_id="12345",
            expiration=datetime(2026, 1, 1, tzinfo=UTC),
        )
        loaded.mark_running()
        loaded.record_notification(at=datetime(2026, 1, 2, tzinfo=UTC))
        uow.monitoring_states.update(loaded)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        updated = uow.monitoring_states.get(state.id)
        assert updated is not None
        assert updated.current_history_id == "12345"
        assert updated.watch_expiration == datetime(2026, 1, 1, tzinfo=UTC)
        assert updated.status.value == "RUNNING"
        assert updated.last_notification_at == datetime(2026, 1, 2, tzinfo=UTC)
        assert updated.last_error is None


def test_monitoring_state_update_missing_raises(db_path: Path) -> None:
    state = MonitoringState.create(account_id="user@example.com")
    with SQLiteUnitOfWork(db_path) as uow, pytest.raises(PersistenceError):
        uow.monitoring_states.update(state)


def test_datetime_round_trip_preserves_instant(db_path: Path) -> None:
    stamp = datetime(2026, 8, 8, 9, 30, 0, tzinfo=UTC)
    event = IntelligenceEvent.create(
        source=_source_ref(),
        title="Timed",
        received_at=stamp,
        source_published_at=stamp,
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.events.add(event)
        uow.commit()
    with SQLiteUnitOfWork(db_path) as uow:
        loaded = uow.events.get(event.id)
        assert loaded is not None
        assert loaded.received_at == stamp
        assert loaded.source_published_at == stamp


def test_custom_profile_generated_content_and_deletion_round_trip(
    db_path: Path,
) -> None:
    profile = AIProfile.create(
        name="VIJAY",
        instructions="Write a Tamil script.",
        output_schema_version="v1",
        output_style=AIOutputStyle.CUSTOM_TEXT,
    )
    event = IntelligenceEvent.create(
        source=_source_ref(),
        title="Headline",
        normalized_content="Body",
        content_hash=ContentHash("abc123"),
        received_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    analysis = AIAnalysis.create(
        event_id=event.id,
        profile_id=profile.id,
        profile_version=1,
        provider="test",
        model="m",
        summary="One line.",
        generated_content="தமிழ் செய்தி\nவரி 2",
    )
    analysis.mark_completed(summary="One line.")
    with SQLiteUnitOfWork(db_path) as uow:
        uow.profiles.add(profile)
        uow.events.add(event)
        uow.analyses.add(analysis)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded_profile = uow.profiles.get(profile.id)
        assert loaded_profile is not None
        assert loaded_profile.output_style is AIOutputStyle.CUSTOM_TEXT
        loaded = uow.analyses.find_latest_by_event(event.id)
        assert loaded is not None
        assert loaded.generated_content == "தமிழ் செய்தி\nவரி 2"
        uow.profiles.delete(profile.id)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.profiles.get(profile.id) is None
        assert uow.profiles.list_all() == []
        # The analysis the deleted profile produced is kept.
        kept = uow.analyses.find_latest_by_event(event.id)
        assert kept is not None
        assert kept.generated_content == "தமிழ் செய்தி\nவரி 2"


def test_clear_all_events_cascades_and_remembers_sources(db_path: Path) -> None:
    profile = AIProfile.create(
        name="General", instructions="Summarize", output_schema_version="v1"
    )
    event = IntelligenceEvent.create(
        source=_source_ref(),
        title="Headline",
        normalized_content="Body",
        content_hash=ContentHash("abc123"),
        received_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    analysis = AIAnalysis.create(
        event_id=event.id,
        profile_id=profile.id,
        profile_version=1,
        provider="test",
        model="m",
        summary="One line.",
        generated_content="Script",
    )
    analysis.mark_completed(summary="One line.")
    notification = Notification.create(
        event_id=event.id, priority=Priority.MEDIUM, title="Toast"
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.profiles.add(profile)
        uow.events.add(event)
        uow.analyses.add(analysis)
        uow.notifications.add(notification)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.events.delete_all() == 1
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.events.list_recent() == []
        assert uow.analyses.find_latest_by_event(event.id) is None
        assert uow.notifications.list_recent() == []
        assert uow.events.was_cleared(
            source_id="gmail-account-1", external_id="msg-100"
        )
        assert not uow.events.was_cleared(
            source_id="gmail-account-1", external_id="msg-other"
        )
        # Clearing notifications on their own leaves nothing else behind.
        assert uow.notifications.delete_all() == 0


def test_app_settings_set_get_delete(db_path: Path) -> None:
    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.app_settings.get("ai.max_output_tokens") is None
        uow.app_settings.set("ai.max_output_tokens", "2048")
        uow.app_settings.set("ai.max_output_tokens", "4096")  # upsert
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.app_settings.get("ai.max_output_tokens") == "4096"
        uow.app_settings.delete("ai.max_output_tokens")
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        assert uow.app_settings.get("ai.max_output_tokens") is None


def test_profile_revision_adds_a_version_and_keeps_the_old_one(
    db_path: Path,
) -> None:
    profile = AIProfile.create(
        name="General", instructions="Summarize", output_schema_version="v1"
    )
    with SQLiteUnitOfWork(db_path) as uow:
        uow.profiles.add(profile)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        loaded = uow.profiles.get(profile.id)
        assert loaded is not None
        loaded.revise(
            name="General", description=None, instructions="Summarize in Tamil"
        )
        uow.profiles.update(loaded)
        uow.commit()

    with SQLiteUnitOfWork(db_path) as uow:
        reloaded = uow.profiles.get(profile.id)
        assert reloaded is not None
        assert reloaded.version == 2
        assert reloaded.instructions == "Summarize in Tamil"
        versions = uow._connection.execute(  # type: ignore[attr-defined]
            "SELECT version_number, system_prompt, is_active "
            "FROM ai_profile_versions WHERE ai_profile_id = ? "
            "ORDER BY version_number",
            (profile.id.value,),
        ).fetchall()
    assert [tuple(row) for row in versions] == [
        (1, "Summarize", 0),
        (2, "Summarize in Tamil", 1),
    ]
