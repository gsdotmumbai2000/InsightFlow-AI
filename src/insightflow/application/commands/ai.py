"""AI analysis application use cases.

``AnalyzeIntelligenceEventUseCase`` is the single orchestration point for
calling an ``AIProvider`` — used identically by the background ``AIWorker``
for both automatic dispatch and manual reprocessing. It never imports a
provider SDK; it only depends on the ``AIProvider`` port.
"""

from __future__ import annotations

import logging
import queue
import time
from collections.abc import Callable
from datetime import UTC, datetime

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.commands.ai_settings import effective_max_output_tokens
from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.dto.mappers import analysis_to_dto
from insightflow.application.dto.models import (
    AIAnalysisDto,
    ReprocessAIRequest,
    ReprocessAIResult,
)
from insightflow.application.exceptions import (
    AIAnalysisNotFoundError,
    AIProfileNotConfiguredError,
    AIProfileNotFoundError,
    AIProviderError,
    AIProviderUnavailableError,
    AIResponseValidationError,
    EventNotFoundError,
)
from insightflow.application.exceptions.ai import AIProviderInvalidResponseError
from insightflow.application.ports.ai import AIProvider
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.ai_dispatch import begin_ai_processing
from insightflow.application.services.ai_prompt_builder import AIPromptBuilder
from insightflow.application.services.ai_response_validator import (
    AIResponseValidator,
    ValidatedAIResult,
)
from insightflow.application.services.monitoring_events import (
    MonitoringEventBroadcaster,
)
from insightflow.domain import (
    AIAnalysis,
    AIProfile,
    AIProfileId,
    EventId,
    IntelligenceEvent,
)
from insightflow.domain.exceptions import InvalidStateTransitionError

logger = logging.getLogger("insightflow.application.ai")

_MAX_FAILURE_REASON_LENGTH = 500


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


class AnalyzeIntelligenceEventUseCase:
    """Loads an event, calls the AI provider, validates, and persists the result.

    Runs on the background ``AIWorker`` thread — never on the Qt GUI thread
    and never inside the Gmail monitoring worker.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provider: AIProvider,
        prompt_builder: AIPromptBuilder,
        validator: AIResponseValidator,
        broadcaster: MonitoringEventBroadcaster,
        *,
        provider_name: str,
        model_id: str,
        max_output_tokens: int,
        temperature: float,
    ) -> None:
        self._uow_factory = uow_factory
        self._provider = provider
        self._prompt_builder = prompt_builder
        self._validator = validator
        self._broadcaster = broadcaster
        self._provider_name = provider_name
        self._model_id = model_id
        self._max_output_tokens = max_output_tokens
        self._temperature = temperature

    def execute(self, job: AIAnalysisJob) -> AIAnalysisDto:
        with use_case_scope("AnalyzeIntelligenceEvent"):
            with unit_of_work_scope(self._uow_factory) as uow:
                event = uow.events.get(EventId(job.event_id))
                if event is None:
                    raise EventNotFoundError(f"Event not found: {job.event_id}")
                profile, profile_version = self._resolve_profile(uow, event, job)
                topic_name: str | None = None
                if event.topic_id is not None:
                    topic = uow.topics.get(event.topic_id)
                    topic_name = topic.name if topic is not None else None
                # Read per job: the Settings page may change it while the
                # Agent is running.
                max_output_tokens = effective_max_output_tokens(
                    uow, self._max_output_tokens
                )

            request = self._prompt_builder.build(
                event=event,
                profile=profile,
                topic_name=topic_name,
                max_output_tokens=max_output_tokens,
                temperature=self._temperature,
            )

            started = time.monotonic()
            try:
                response = self._provider.analyze(request)
            except AIProviderError as exc:
                # Invalid-response messages are our own adapter text (never
                # raw model output), so they are safe and worth showing.
                detail = (
                    str(exc)
                    if isinstance(exc, AIProviderInvalidResponseError)
                    else "provider error"
                )
                return self._finish(
                    event_id=job.event_id,
                    profile=profile,
                    profile_version=profile_version,
                    completed=False,
                    latency_ms=_elapsed_ms(started),
                    failure_reason=f"{type(exc).__name__}: {detail}",
                )

            latency_ms = _elapsed_ms(started)
            try:
                validated = self._validator.validate(
                    response, output_style=profile.output_style
                )
            except AIResponseValidationError as exc:
                return self._finish(
                    event_id=job.event_id,
                    profile=profile,
                    profile_version=profile_version,
                    completed=False,
                    latency_ms=latency_ms,
                    failure_reason=f"Invalid AI response: {exc}",
                )

            return self._finish(
                event_id=job.event_id,
                profile=profile,
                profile_version=profile_version,
                completed=True,
                latency_ms=latency_ms,
                validated=validated,
            )

    def _resolve_profile(
        self, uow: UnitOfWork, event: IntelligenceEvent, job: AIAnalysisJob
    ) -> tuple[AIProfile, int]:
        if job.ai_profile_id is not None:
            profile = uow.profiles.get(AIProfileId(job.ai_profile_id))
            if profile is None:
                raise AIProfileNotFoundError(
                    f"AI profile not found: {job.ai_profile_id}"
                )
            return profile, job.profile_version or profile.version

        if event.topic_id is None:
            raise AIProfileNotConfiguredError(
                f"Event {job.event_id} has no topic; cannot resolve an AI profile."
            )
        topic = uow.topics.get(event.topic_id)
        if topic is None or topic.ai_profile_id is None:
            raise AIProfileNotConfiguredError(
                f"No AI profile configured for the topic of event {job.event_id}."
            )
        profile = uow.profiles.get(topic.ai_profile_id)
        if profile is None:
            raise AIProfileNotConfiguredError(
                f"Configured AI profile not found for event {job.event_id}."
            )
        if not profile.enabled:
            raise AIProfileNotConfiguredError(
                f"AI profile is disabled for event {job.event_id}."
            )
        return profile, profile.version

    def _finish(
        self,
        *,
        event_id: str,
        profile: AIProfile,
        profile_version: int,
        completed: bool,
        latency_ms: int,
        validated: ValidatedAIResult | None = None,
        failure_reason: str | None = None,
    ) -> AIAnalysisDto:
        with unit_of_work_scope(self._uow_factory) as uow:
            if completed:
                assert validated is not None
                analysis = AIAnalysis.create(
                    event_id=EventId(event_id),
                    profile_id=profile.id,
                    profile_version=profile_version,
                    provider=self._provider_name,
                    model=self._model_id,
                    summary=validated.summary,
                    why_it_matters=validated.why_it_matters,
                    key_facts=validated.key_facts,
                    what_to_watch=validated.what_to_watch,
                    market_impact=validated.market_impact,
                    entities=validated.entities,
                    sentiment=validated.sentiment,
                    confidence=validated.confidence,
                    latency_ms=latency_ms,
                    generated_content=validated.generated_content,
                )
                analysis.mark_completed(summary=validated.summary)
            else:
                analysis = AIAnalysis.create(
                    event_id=EventId(event_id),
                    profile_id=profile.id,
                    profile_version=profile_version,
                    provider=self._provider_name,
                    model=self._model_id,
                    latency_ms=latency_ms,
                )
                analysis.mark_failed(
                    reason=_sanitize_failure_reason(
                        failure_reason or "Unknown AI failure"
                    )
                )
            uow.analyses.add(analysis)

            event = uow.events.get(EventId(event_id))
            if event is not None:
                try:
                    if completed:
                        event.mark_completed()
                    else:
                        event.mark_failed()
                    uow.events.update(event)
                except InvalidStateTransitionError:
                    logger.debug(
                        "Event status transition skipped event_id=%s completed=%s",
                        event_id,
                        completed,
                    )
            uow.commit()

        self._broadcaster.notify(
            "ai_analysis_completed" if completed else "ai_analysis_failed"
        )
        return analysis_to_dto(analysis)


class ReprocessAIAnalysisUseCase:
    """Queue an event for (re-)analysis. Never calls the provider directly.

    Enqueuing is fast (a DB read plus a queue put) so this is safe to call
    synchronously from the Qt GUI thread; the actual AI call happens on the
    background ``AIWorker`` thread via ``AnalyzeIntelligenceEventUseCase``.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        enqueue: Callable[[AIAnalysisJob], None],
        *,
        ai_enabled: bool,
    ) -> None:
        self._uow_factory = uow_factory
        self._enqueue = enqueue
        self._ai_enabled = ai_enabled

    def execute(self, request: ReprocessAIRequest) -> ReprocessAIResult:
        with use_case_scope("ReprocessAIAnalysis"):

            def _run() -> ReprocessAIResult:
                with unit_of_work_scope(self._uow_factory) as uow:
                    event = uow.events.get(EventId(request.event_id))
                    if event is None:
                        raise EventNotFoundError(f"Event not found: {request.event_id}")
                    if not self._ai_enabled:
                        raise AIProviderUnavailableError(
                            "AI analysis is disabled in settings."
                        )
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
                    else:
                        if event.topic_id is None:
                            raise AIProfileNotConfiguredError(
                                f"Event {request.event_id} has no topic; "
                                "specify ai_profile_id explicitly."
                            )
                        topic = uow.topics.get(event.topic_id)
                        if topic is None or topic.ai_profile_id is None:
                            raise AIProfileNotConfiguredError(
                                "No AI profile configured for the topic of "
                                f"event {request.event_id}."
                            )
                        profile = uow.profiles.get(topic.ai_profile_id)
                        if profile is None:
                            raise AIProfileNotConfiguredError(
                                "Configured AI profile not found for event "
                                f"{request.event_id}."
                            )
                        profile_id = profile.id.value
                        profile_version = profile.version
                    begin_ai_processing(uow, event)

                try:
                    self._enqueue(
                        AIAnalysisJob(
                            event_id=request.event_id,
                            ai_profile_id=profile_id,
                            profile_version=profile_version,
                            manual=True,
                        )
                    )
                except queue.Full as exc:
                    raise AIProviderUnavailableError(
                        "AI processing queue is full; try again shortly."
                    ) from exc

                return ReprocessAIResult(
                    event_id=request.event_id,
                    status="QUEUED",
                    ai_profile_id=profile_id,
                    profile_version=profile_version,
                    requested_at=datetime.now(UTC),
                    message=(
                        "AI (re-)analysis has been queued and will run in "
                        "the background."
                    ),
                )

            return run_mutating(_run)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _sanitize_failure_reason(reason: str) -> str:
    """Cap length defensively; callers already avoid embedding raw content."""
    cleaned = reason.strip() or "Unknown AI failure"
    if len(cleaned) > _MAX_FAILURE_REASON_LENGTH:
        return cleaned[:_MAX_FAILURE_REASON_LENGTH] + "..."
    return cleaned
