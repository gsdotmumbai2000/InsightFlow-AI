"""AI analysis application use cases (no provider calls)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.mappers import analysis_to_dto
from insightflow.application.dto.models import (
    AIAnalysisDto,
    ReprocessAIRequest,
    ReprocessAIResult,
)
from insightflow.application.exceptions import (
    AIAnalysisNotFoundError,
    AIProfileNotFoundError,
    EventNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import AIProfileId, EventId


class GetAIAnalysisUseCase:
    """Return the latest persisted AI analysis for an event."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> AIAnalysisDto:
        with (
            use_case_scope("GetAIAnalysis"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            if uow.events.get(EventId(event_id)) is None:
                raise EventNotFoundError(f"Event not found: {event_id}")
            analysis = uow.analyses.find_latest_by_event(EventId(event_id))
            if analysis is None:
                raise AIAnalysisNotFoundError(
                    f"AI analysis not found for event: {event_id}"
                )
            return analysis_to_dto(analysis)


class ReprocessAIAnalysisUseCase:
    """Record an application-level reprocess intent (no AI worker yet)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: ReprocessAIRequest) -> ReprocessAIResult:
        with use_case_scope("ReprocessAIAnalysis"):

            def _run() -> ReprocessAIResult:
                with unit_of_work_scope(self._uow_factory) as uow:
                    event = uow.events.get(EventId(request.event_id))
                    if event is None:
                        raise EventNotFoundError(f"Event not found: {request.event_id}")
                    profile_id = request.ai_profile_id
                    profile_version = request.profile_version
                    if profile_id is not None:
                        profile = uow.profiles.get(AIProfileId(profile_id))
                        if profile is None:
                            raise AIProfileNotFoundError(
                                f"AI profile not found: {profile_id}"
                            )
                        if profile_version is None:
                            profile_version = profile.version
                    return ReprocessAIResult(
                        event_id=event.id.value,
                        status="REQUESTED",
                        ai_profile_id=profile_id,
                        profile_version=profile_version,
                        requested_at=datetime.now(UTC),
                        message=(
                            "AI reprocess intent recorded; "
                            "no AI worker is available in Phase 5."
                        ),
                    )

            return run_mutating(_run)
