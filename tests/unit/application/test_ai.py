"""AI analysis application use-case tests (Phase 11)."""

from __future__ import annotations

import queue

import pytest
from tests.fakes.ai import FakeAIProvider, make_response
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.commands.ai import ReprocessAIAnalysisUseCase
from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
    ReprocessAIRequest,
)
from insightflow.application.exceptions import (
    AIAnalysisNotFoundError,
    AIProfileNotConfiguredError,
    AIProfileNotFoundError,
    AIProviderUnavailableError,
    EventNotFoundError,
)
from insightflow.application.exceptions.ai import AIProviderTimeoutError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import AIAnalysis, AIProfile, EventId


def _add_profile(store: InMemoryStore, **overrides: object) -> AIProfile:
    profile = AIProfile.create(
        name=str(overrides.get("name", "Default")),
        instructions=str(overrides.get("instructions", "Summarize the event.")),
        output_schema_version="v1",
        enabled=bool(overrides.get("enabled", True)),
    )
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.commit()
    return profile


def _create_event_with_profile(
    use_cases: ApplicationUseCases, store: InMemoryStore, *, external_id: str
) -> tuple[str, AIProfile]:
    profile = _add_profile(store)
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Topic",
            source_type="GENERIC",
            source_id="src",
            source_identifier=external_id,
            ai_profile_id=profile.id.value,
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="src",
            external_id=external_id,
            topic_id=topic.id,
            title="An event",
            normalized_content="Something happened worth analyzing.",
        )
    )
    return event.id, profile


def test_get_analysis(use_cases: ApplicationUseCases, store: InMemoryStore) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-ai",
            title="AI event",
        )
    )
    profile = AIProfile.create(
        name="Default", instructions="Summarize", output_schema_version="v1"
    )
    analysis = AIAnalysis.create(
        event_id=EventId(event.id),
        profile_id=profile.id,
        profile_version=profile.version,
        provider="test",
        model="test-model",
    )
    analysis.mark_completed(summary="Summary")
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.analyses.add(analysis)
        uow.commit()

    loaded = use_cases.get_ai_analysis.execute(event.id)
    assert loaded.summary == "Summary"
    assert loaded.status == "COMPLETED"


def test_analysis_not_found(use_cases: ApplicationUseCases) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-none",
        )
    )
    with pytest.raises(AIAnalysisNotFoundError):
        use_cases.get_ai_analysis.execute(event.id)


# -- AnalyzeIntelligenceEventUseCase -----------------------------------------


def test_analyze_success_persists_completed_analysis(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e1")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(summary="Concise summary.", confidence=0.7)

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "COMPLETED"
    assert dto.summary == "Concise summary."
    assert dto.confidence == pytest.approx(0.7)
    updated_event = use_cases.get_intelligence_event.execute(event_id)
    assert updated_event.status == "COMPLETED"


def test_analyze_provider_error_marks_analysis_and_event_failed(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e2")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.error = AIProviderTimeoutError("AWS Bedrock request timed out.")

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "FAILED"
    assert dto.failure_reason is not None
    assert "AIProviderTimeoutError" in dto.failure_reason
    updated_event = use_cases.get_intelligence_event.execute(event_id)
    assert updated_event.status == "FAILED"


def test_analyze_invalid_sentiment_marks_failed(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e3")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(sentiment="VERY_HAPPY")

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "FAILED"
    assert dto.failure_reason is not None
    assert "Invalid AI response" in dto.failure_reason


def test_analyze_invalid_confidence_marks_failed(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e4")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(confidence=5.0)

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "FAILED"


def test_analyze_partial_market_impact_marks_failed(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e5")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(market_impact_direction="BULLISH")

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "FAILED"


def test_analyze_missing_profile_raises(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="src",
            external_id="e6",
        )
    )
    with pytest.raises(AIProfileNotConfiguredError):
        use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event.id))


def test_reanalysis_from_completed_event_creates_new_analysis(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="e7")
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(summary="First pass.")
    first = use_cases.analyze_intelligence_event.execute(
        AIAnalysisJob(event_id=event_id)
    )
    assert first.status == "COMPLETED"

    # Manual re-analysis restarts AI_PROCESSING even though the event and
    # its first analysis already reached a terminal state.
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(summary="Second pass.")
    second = use_cases.analyze_intelligence_event.execute(
        AIAnalysisJob(event_id=event_id)
    )

    assert second.status == "COMPLETED"
    assert second.summary == "Second pass."
    latest = use_cases.get_ai_analysis.execute(event_id)
    assert latest.summary == "Second pass."


# -- ReprocessAIAnalysisUseCase (unit-tested directly, isolated queue) ------


def test_reprocess_queues_job_using_topic_profile(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event_id, profile = _create_event_with_profile(use_cases, store, external_id="r1")
    jobs: list[AIAnalysisJob] = []
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, jobs.append, ai_enabled=True
    )

    result = use_case.execute(ReprocessAIRequest(event_id=event_id))

    assert result.status == "QUEUED"
    assert result.ai_profile_id == profile.id.value
    assert jobs == [
        AIAnalysisJob(
            event_id=event_id,
            ai_profile_id=profile.id.value,
            profile_version=profile.version,
            manual=True,  # an explicit Analyze click
        )
    ]
    updated_event = use_cases.get_intelligence_event.execute(event_id)
    assert updated_event.status == "AI_PROCESSING"


def test_reprocess_with_explicit_profile_id(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC", source_id="src", external_id="r2"
        )
    )
    profile = _add_profile(store, name="Explicit")
    jobs: list[AIAnalysisJob] = []
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, jobs.append, ai_enabled=True
    )

    result = use_case.execute(
        ReprocessAIRequest(event_id=event.id, ai_profile_id=profile.id.value)
    )

    assert result.ai_profile_id == profile.id.value
    assert jobs[0].ai_profile_id == profile.id.value


def test_reprocess_unknown_profile_id_raises(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC", source_id="src", external_id="r3"
        )
    )
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, lambda job: None, ai_enabled=True
    )
    with pytest.raises(AIProfileNotFoundError):
        use_case.execute(
            ReprocessAIRequest(event_id=event.id, ai_profile_id="missing-profile")
        )


def test_reprocess_no_profile_configured_raises(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC", source_id="src", external_id="r4"
        )
    )
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, lambda job: None, ai_enabled=True
    )
    with pytest.raises(AIProfileNotConfiguredError):
        use_case.execute(ReprocessAIRequest(event_id=event.id))


def test_reprocess_event_not_found(store: InMemoryStore) -> None:
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, lambda job: None, ai_enabled=True
    )
    with pytest.raises(EventNotFoundError):
        use_case.execute(ReprocessAIRequest(event_id="missing"))


def test_reprocess_raises_when_ai_disabled(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC", source_id="src", external_id="r5"
        )
    )
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, lambda job: None, ai_enabled=False
    )
    with pytest.raises(AIProviderUnavailableError):
        use_case.execute(ReprocessAIRequest(event_id=event.id))


def test_reprocess_raises_when_queue_full(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event_id, _profile = _create_event_with_profile(use_cases, store, external_id="r6")
    bounded: queue.Queue[AIAnalysisJob] = queue.Queue(maxsize=1)
    bounded.put_nowait(AIAnalysisJob(event_id="already-queued"))
    use_case = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, bounded.put_nowait, ai_enabled=True
    )
    with pytest.raises(AIProviderUnavailableError):
        use_case.execute(ReprocessAIRequest(event_id=event_id))
