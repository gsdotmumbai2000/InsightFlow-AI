"""Custom-text AI profiles and AI profile deletion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.fakes.ai import FakeAIProvider, make_response
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.dto.models import (
    CreateAIProfileRequest,
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
    UpdateAIProfileRequest,
)
from insightflow.application.exceptions import (
    AIProfileNotFoundError,
    ApplicationValidationError,
)
from insightflow.application.exceptions.ai import AIResponseValidationError
from insightflow.application.services.ai_prompt_builder import AIPromptBuilder
from insightflow.application.services.ai_response_validator import (
    AIResponseValidator,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import (
    AIOutputStyle,
    AIProfile,
    IntelligenceEvent,
    SourceReference,
    SourceType,
)

_TAMIL_SCRIPT = "தமிழ்நாடு முதல்வர் விஜய்...\nமேலும் செய்திகள்"


def _event() -> IntelligenceEvent:
    return IntelligenceEvent.create(
        source=SourceReference(
            source_type=SourceType.GENERIC, source_id="src", external_id="ext-1"
        ),
        title="Google Alert - cm vijay",
        normalized_content="CM Vijay meets Naidu on Krishna water sharing.",
        received_at=datetime.now(UTC),
    )


def _custom_profile() -> AIProfile:
    return AIProfile.create(
        name="VIJAY",
        instructions="Write a Tamil flash news script for YouTube Shorts.",
        output_schema_version="v1",
        output_style=AIOutputStyle.CUSTOM_TEXT,
    )


# -- Prompt and validation ------------------------------------------------


def test_custom_text_prompt_asks_only_for_the_requested_text() -> None:
    request = AIPromptBuilder().build(
        event=_event(),
        profile=_custom_profile(),
        topic_name="VIJAY",
        max_output_tokens=4096,
        temperature=0.2,
    )
    prompt = request.system_instructions
    assert "Write a Tamil flash news script" in prompt
    assert '"generated_content"' in prompt
    assert "market_impact" not in prompt
    assert '"sentiment"' not in prompt


def test_analysis_prompt_is_unchanged_for_analysis_profiles() -> None:
    profile = AIProfile.create(
        name="Markets", instructions="Analyze.", output_schema_version="v1"
    )
    request = AIPromptBuilder().build(
        event=_event(),
        profile=profile,
        topic_name="TRUMP",
        max_output_tokens=1024,
        temperature=0.2,
    )
    assert "market_impact_direction" in request.system_instructions
    assert '"generated_content"' not in request.system_instructions


def test_custom_text_validation_requires_generated_content() -> None:
    with pytest.raises(AIResponseValidationError):
        AIResponseValidator().validate(
            make_response(generated_content=None),
            output_style=AIOutputStyle.CUSTOM_TEXT,
        )


def test_custom_text_validation_ignores_analysis_fields() -> None:
    result = AIResponseValidator().validate(
        make_response(
            generated_content=_TAMIL_SCRIPT,
            sentiment="not-a-sentiment",  # would fail ANALYSIS validation
            market_impact_direction="BULLISH",  # partial market impact
        ),
        output_style=AIOutputStyle.CUSTOM_TEXT,
    )
    assert result.generated_content == _TAMIL_SCRIPT
    assert result.market_impact is None
    assert result.sentiment is None


def test_custom_text_summary_falls_back_to_first_line() -> None:
    result = AIResponseValidator().validate(
        make_response(summary="", generated_content=_TAMIL_SCRIPT),
        output_style=AIOutputStyle.CUSTOM_TEXT,
    )
    assert result.summary == "தமிழ்நாடு முதல்வர் விஜய்..."


# -- Use cases ------------------------------------------------------------


def _create_topic_and_event(
    use_cases: ApplicationUseCases, *, profile_id: str, external_id: str = "e1"
) -> tuple[str, str]:
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="VIJAY",
            source_type="GENERIC",
            source_id="src",
            source_identifier=f"label-{external_id}",
            ai_profile_id=profile_id,
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="src",
            external_id=external_id,
            topic_id=topic.id,
            title="Google Alert - cm vijay",
            normalized_content="CM Vijay meets Naidu on Krishna water sharing.",
        )
    )
    return topic.id, event.id


def test_custom_text_profile_analysis_stores_generated_content(
    use_cases: ApplicationUseCases, ai_provider: FakeAIProvider
) -> None:
    profile = use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(
            name="VIJAY",
            instructions="Write a Tamil flash news script.",
            output_style="CUSTOM_TEXT",
        )
    )
    assert profile.output_style == "CUSTOM_TEXT"
    _, event_id = _create_topic_and_event(use_cases, profile_id=profile.id)
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response(
        summary="CM Vijay to meet Naidu.", generated_content=_TAMIL_SCRIPT
    )

    dto = use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    assert dto.status == "COMPLETED"
    assert dto.generated_content == _TAMIL_SCRIPT
    assert dto.market_impact is None
    assert use_cases.get_ai_analysis.execute(event_id).generated_content == (
        _TAMIL_SCRIPT
    )


def test_changing_output_style_starts_a_new_version(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(name="VIJAY", instructions="Write a script.")
    )
    updated = use_cases.update_ai_profile.execute(
        UpdateAIProfileRequest(
            profile_id=created.id,
            name="VIJAY",
            instructions="Write a script.",
            output_style="CUSTOM_TEXT",
        )
    )
    assert updated.output_style == "CUSTOM_TEXT"
    assert updated.version == 2


def test_unknown_output_style_is_rejected(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.create_ai_profile.execute(
            CreateAIProfileRequest(
                name="X", instructions="Y", output_style="POETRY_ONLY"
            )
        )


def test_delete_profile_unassigns_topics_and_keeps_analyses(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    profile = use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(name="VIJAY", instructions="Summarize.")
    )
    topic_id, event_id = _create_topic_and_event(use_cases, profile_id=profile.id)
    use_cases.mark_event_processing.execute(event_id)
    ai_provider.response = make_response()
    use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event_id))

    use_cases.delete_ai_profile.execute(profile.id)

    assert use_cases.get_topic.execute(topic_id).ai_profile_id is None
    assert all(item.id != profile.id for item in use_cases.list_ai_profiles.execute())
    with pytest.raises(AIProfileNotFoundError):
        use_cases.get_ai_profile.execute(profile.id)
    # The earlier analysis still shows on its event.
    assert use_cases.get_ai_analysis.execute(event_id).status == "COMPLETED"


def test_deleted_profile_name_can_be_reused(use_cases: ApplicationUseCases) -> None:
    first = use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(name="VIJAY", instructions="Old prompt.")
    )
    use_cases.delete_ai_profile.execute(first.id)

    second = use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(
            name="VIJAY", instructions="New prompt.", output_style="CUSTOM_TEXT"
        )
    )

    names = [item.name for item in use_cases.list_ai_profiles.execute()]
    assert names == ["VIJAY"]
    assert second.id != first.id


def test_delete_unknown_profile_raises(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(AIProfileNotFoundError):
        use_cases.delete_ai_profile.execute("missing-profile-id")
