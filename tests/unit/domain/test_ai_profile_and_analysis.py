"""AIProfile and AIAnalysis tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from insightflow.domain import (
    AIAnalysis,
    AIAnalysisStatus,
    AIProfile,
    Confidence,
    DomainValidationError,
    EventId,
    InvalidStateTransitionError,
    MarketImpact,
    MarketImpactDirection,
    Sentiment,
)


def test_ai_profile_valid_creation() -> None:
    profile = AIProfile.create(
        name="General News",
        instructions="Summarize clearly and separate facts from interpretation.",
        output_schema_version="v1",
    )
    assert profile.version == 1
    assert profile.enabled is True


def test_ai_profile_invalid_name() -> None:
    with pytest.raises(DomainValidationError, match="name"):
        AIProfile.create(
            name="",
            instructions="Instructions",
            output_schema_version="v1",
        )


def test_ai_profile_version_validation() -> None:
    with pytest.raises(DomainValidationError, match="version"):
        AIProfile.create(
            name="General",
            instructions="Instructions",
            output_schema_version="v1",
            version=0,
        )


def test_ai_analysis_valid_creation_and_complete() -> None:
    profile = AIProfile.create(
        name="General",
        instructions="Analyze",
        output_schema_version="v1",
    )
    analysis = AIAnalysis.create(
        event_id=EventId.generate(),
        profile_id=profile.id,
        profile_version=profile.version,
        provider="test-provider",
        model="test-model",
        key_facts=("Fact one",),
        why_it_matters="Context for the user",
        confidence=Confidence(0.8),
        sentiment=Sentiment.NEUTRAL,
    )
    assert analysis.status is AIAnalysisStatus.PENDING
    analysis.mark_completed(summary="Short summary")
    assert analysis.status is AIAnalysisStatus.COMPLETED
    assert analysis.summary == "Short summary"


def test_confidence_boundaries() -> None:
    assert Confidence(0).value == 0.0
    assert Confidence(1).value == 1.0
    with pytest.raises(DomainValidationError):
        Confidence(-0.01)
    with pytest.raises(DomainValidationError):
        Confidence(1.01)


def test_ai_analysis_status_transitions() -> None:
    analysis = AIAnalysis.create(
        event_id=EventId.generate(),
        profile_id=AIProfile.create(
            name="General",
            instructions="Analyze",
            output_schema_version="v1",
        ).id,
        profile_version=1,
        provider="provider",
        model="model",
        summary="Draft",
    )
    analysis.mark_failed(reason="provider timeout")
    assert analysis.status is AIAnalysisStatus.FAILED
    with pytest.raises(InvalidStateTransitionError):
        analysis.mark_completed(summary="Too late")


def test_market_impact_valid_and_invalid_confidence() -> None:
    impact = MarketImpact(
        relevance="Moderate",
        direction=MarketImpactDirection.UNCERTAIN,
        affected_assets=("equities",),
        reasoning="Mixed signals",
        confidence=Confidence(0.5),
    )
    assert impact.direction is MarketImpactDirection.UNCERTAIN
    with pytest.raises(DomainValidationError):
        MarketImpact(
            relevance="High",
            direction=MarketImpactDirection.BULLISH,
            affected_assets=("oil",),
            reasoning="Speculative",
            confidence=Confidence(2.0),
        )


def test_market_impact_directions() -> None:
    for direction in MarketImpactDirection:
        impact = MarketImpact(
            relevance="Relevant",
            direction=direction,
            affected_assets=("asset-a",),
            reasoning="Interpretive only",
            confidence=Confidence(0.4),
        )
        assert impact.direction is direction


def test_naive_timestamp_rejected_on_analysis() -> None:
    profile = AIProfile.create(
        name="General",
        instructions="Analyze",
        output_schema_version="v1",
    )
    with pytest.raises(DomainValidationError, match="timezone-aware"):
        AIAnalysis(
            id=AIAnalysis.create(
                event_id=EventId.generate(),
                profile_id=profile.id,
                profile_version=1,
                provider="p",
                model="m",
            ).id,
            event_id=EventId.generate(),
            profile_id=profile.id,
            profile_version=1,
            provider="p",
            model="m",
            summary="s",
            why_it_matters=None,
            key_facts=(),
            what_to_watch=(),
            market_impact=None,
            entities=(),
            sentiment=None,
            confidence=None,
            status=AIAnalysisStatus.PENDING,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
