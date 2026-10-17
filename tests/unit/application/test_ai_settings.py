"""AI output token limit setting tests (Settings page override)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.fakes.ai import FakeAIProvider
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.commands.ai import ReprocessAIAnalysisUseCase
from insightflow.application.commands.ai_settings import MAX_OUTPUT_TOKENS_KEY
from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
    ReprocessAIRequest,
)
from insightflow.application.exceptions import ApplicationValidationError
from insightflow.application.services.ai_dispatch import (
    AIAnalysisDispatcher,
    ai_job_should_run,
    find_pending_ai_jobs,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import AIProfile, EventId, IntelligenceEventCreated, TopicId


def test_limit_defaults_to_configured_value(use_cases: ApplicationUseCases) -> None:
    limit = use_cases.get_ai_output_token_limit.execute()

    assert limit.effective == use_cases.ai_settings.max_output_tokens
    assert limit.configured_default == use_cases.ai_settings.max_output_tokens
    assert limit.overridden is False


def test_set_limit_overrides_and_reset_restores_default(
    use_cases: ApplicationUseCases,
) -> None:
    saved = use_cases.set_ai_output_token_limit.execute(4096)
    assert saved.effective == 4096
    assert saved.overridden is True
    assert use_cases.get_ai_output_token_limit.execute().effective == 4096

    reset = use_cases.set_ai_output_token_limit.execute(None)
    assert reset.overridden is False
    assert reset.effective == use_cases.ai_settings.max_output_tokens


@pytest.mark.parametrize("value", [0, 63, 64_001])
def test_set_limit_rejects_out_of_range(
    use_cases: ApplicationUseCases, value: int
) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.set_ai_output_token_limit.execute(value)


def test_invalid_stored_value_falls_back_to_default(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    store.app_settings.set(MAX_OUTPUT_TOKENS_KEY, "not-a-number")

    limit = use_cases.get_ai_output_token_limit.execute()

    assert limit.effective == use_cases.ai_settings.max_output_tokens


def test_ai_analysis_is_enabled_by_default_and_can_be_toggled(
    use_cases: ApplicationUseCases,
) -> None:
    assert use_cases.get_ai_analysis_enabled.execute() is True
    assert use_cases.set_ai_analysis_enabled.execute(False) == 0  # none waiting
    assert use_cases.get_ai_analysis_enabled.execute() is False
    use_cases.set_ai_analysis_enabled.execute(True)
    assert use_cases.get_ai_analysis_enabled.execute() is True


def _event_with_profile(
    use_cases: ApplicationUseCases, store: InMemoryStore, *, external_id: str
) -> tuple[str, str]:
    profile = AIProfile.create(
        name="Default", instructions="Summarize.", output_schema_version="v1"
    )
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.commit()
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Topic",
            source_type="GENERIC",
            source_id="src",
            source_identifier=f"t-{external_id}",
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
            normalized_content="Something happened.",
        )
    )
    return topic.id, event.id


def test_analyze_click_still_runs_while_automatic_ai_is_off(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    _, event_id = _event_with_profile(use_cases, store, external_id="off-1")
    use_cases.set_ai_analysis_enabled.execute(False)
    jobs: list[AIAnalysisJob] = []
    reprocess = ReprocessAIAnalysisUseCase(
        store.unit_of_work_factory, jobs.append, ai_enabled=True
    )

    assert reprocess.execute(ReprocessAIRequest(event_id=event_id)).status == "QUEUED"

    assert len(jobs) == 1
    assert jobs[0].manual is True
    assert ai_job_should_run(store.unit_of_work_factory, jobs[0]) is True


def test_turning_off_cancels_the_waiting_backlog(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    """Re-enabling later must not work through a large, costly backlog."""
    waiting = []
    for index in range(3):
        _, event_id = _event_with_profile(use_cases, store, external_id=f"b-{index}")
        use_cases.mark_event_processing.execute(event_id)
        waiting.append(event_id)

    cancelled = use_cases.set_ai_analysis_enabled.execute(False)

    assert cancelled == 3
    for event_id in waiting:
        assert use_cases.get_intelligence_event.execute(event_id).status == "RECEIVED"
    use_cases.set_ai_analysis_enabled.execute(True)
    # Turning it back on picks nothing up: nothing is waiting any more.
    assert find_pending_ai_jobs(store.unit_of_work_factory) == []


def test_automatic_job_already_queued_is_dropped_once_ai_is_off(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    _, event_id = _event_with_profile(use_cases, store, external_id="q-1")
    use_cases.mark_event_processing.execute(event_id)
    automatic_job = AIAnalysisJob(event_id=event_id)  # queued before turning off
    store.app_settings.set("ai.analysis_enabled", "false")  # without cancel step

    assert ai_job_should_run(store.unit_of_work_factory, automatic_job) is False
    # Its event is cancelled too, so no later scan re-finds it.
    assert use_cases.get_intelligence_event.execute(event_id).status == "RECEIVED"
    assert find_pending_ai_jobs(store.unit_of_work_factory) == []


def test_new_events_are_not_dispatched_while_ai_is_off(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    topic_id, event_id = _event_with_profile(use_cases, store, external_id="off-2")
    use_cases.set_ai_analysis_enabled.execute(False)
    enqueued: list[AIAnalysisJob] = []
    dispatcher = AIAnalysisDispatcher(
        store.unit_of_work_factory, enqueued.append, enabled=True
    )

    dispatcher.dispatch(
        IntelligenceEventCreated(
            event_id=EventId(event_id),
            topic_id=TopicId(topic_id),
            occurred_at=datetime.now(UTC),
        )
    )

    assert enqueued == []
    assert use_cases.get_intelligence_event.execute(event_id).status == "RECEIVED"


def test_analysis_uses_the_saved_limit(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    ai_provider: FakeAIProvider,
) -> None:
    profile = AIProfile.create(
        name="Default", instructions="Summarize.", output_schema_version="v1"
    )
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.commit()
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Topic",
            source_type="GENERIC",
            source_id="src",
            source_identifier="t1",
            ai_profile_id=profile.id.value,
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="src",
            external_id="e1",
            topic_id=topic.id,
            title="An event",
            normalized_content="Something happened.",
        )
    )
    use_cases.mark_event_processing.execute(event.id)
    use_cases.set_ai_output_token_limit.execute(4096)

    use_cases.analyze_intelligence_event.execute(AIAnalysisJob(event_id=event.id))

    assert ai_provider.requests[-1].max_output_tokens == 4096
