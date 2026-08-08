"""SQLite repository integration and round-trip tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from insightflow.application.exceptions import DuplicateEntityError
from insightflow.domain import (
    AIAnalysis,
    AIProfile,
    Attachment,
    Confidence,
    ContentHash,
    EventProcessingStatus,
    IntelligenceEvent,
    MarketImpact,
    MarketImpactDirection,
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
