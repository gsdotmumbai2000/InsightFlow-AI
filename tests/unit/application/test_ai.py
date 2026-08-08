"""AI analysis use-case unit tests (no provider calls)."""

from __future__ import annotations

import pytest
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    ReprocessAIRequest,
)
from insightflow.application.exceptions import (
    AIAnalysisNotFoundError,
    EventNotFoundError,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import AIAnalysis, AIProfile, EventId


def test_get_analysis_and_reprocess(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-ai",
            title="AI event",
        )
    )
    profile = AIProfile.create(
        name="Default",
        instructions="Summarize",
        output_schema_version="v1",
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

    result = use_cases.reprocess_ai_analysis.execute(
        ReprocessAIRequest(event_id=event.id, ai_profile_id=profile.id.value)
    )
    assert result.status == "REQUESTED"
    assert result.ai_profile_id == profile.id.value
    assert result.profile_version == profile.version


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


def test_reprocess_event_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(EventNotFoundError):
        use_cases.reprocess_ai_analysis.execute(ReprocessAIRequest(event_id="missing"))
