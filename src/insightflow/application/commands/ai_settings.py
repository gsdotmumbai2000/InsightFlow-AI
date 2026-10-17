"""User-adjustable AI settings (Settings page).

The configured value (``INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS`` / ``.env``) is the
default; a value saved from the Settings page overrides it. The override is
persisted in ``app_settings`` because the Desktop (which saves it) and the
Background Agent (which runs analyses) are separate processes — the Agent
reads it for every analysis, so a change applies without a restart.
"""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.ai import AIOutputTokenLimitDto
from insightflow.application.exceptions import ApplicationValidationError
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import EventProcessingStatus

MAX_OUTPUT_TOKENS_KEY = "ai.max_output_tokens"
ANALYSIS_ENABLED_KEY = "ai.analysis_enabled"
# Same lower bound the configuration loader enforces for the .env value.
MIN_OUTPUT_TOKENS = 64
MAX_OUTPUT_TOKENS = 64_000
# Far above any realistic backlog; bounds one transaction.
_CANCEL_BATCH_LIMIT = 100_000


def effective_max_output_tokens(uow: UnitOfWork, configured_default: int) -> int:
    """The saved override if present and valid, else ``configured_default``."""
    raw = uow.app_settings.get(MAX_OUTPUT_TOKENS_KEY)
    if raw is None:
        return configured_default
    try:
        value = int(raw)
    except ValueError:
        return configured_default
    if not MIN_OUTPUT_TOKENS <= value <= MAX_OUTPUT_TOKENS:
        return configured_default
    return value


def ai_analysis_enabled(uow: UnitOfWork) -> bool:
    """Whether *automatic* AI analysis of new emails is on (default: on).

    Separate from ``INSIGHTFLOW_AI_ENABLED``, which decides whether AI is
    available at all. This Settings-page switch only stops automatic
    analysis (and its cost); an explicit Analyze click always runs.
    """
    return uow.app_settings.get(ANALYSIS_ENABLED_KEY) != "false"


def ai_analysis_enabled_now(uow_factory: Callable[[], UnitOfWork]) -> bool:
    with unit_of_work_scope(uow_factory) as uow:
        return ai_analysis_enabled(uow)


class GetAIAnalysisEnabledUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self) -> bool:
        with use_case_scope("GetAIAnalysisEnabled"):
            return ai_analysis_enabled_now(self._uow_factory)


class SetAIAnalysisEnabledUseCase:
    """Turn automatic AI analysis on or off; the Agent applies it at once.

    Turning it off also cancels every analysis still waiting to run (events
    in AI_PROCESSING go back to RECEIVED), so turning it on later never
    works through a possibly large, costly backlog — only emails arriving
    after that are analyzed automatically. Returns how many waiting
    analyses were cancelled.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, enabled: bool) -> int:
        with use_case_scope("SetAIAnalysisEnabled"):

            def _run() -> int:
                with unit_of_work_scope(self._uow_factory) as uow:
                    cancelled = 0
                    if enabled:
                        uow.app_settings.delete(ANALYSIS_ENABLED_KEY)
                    else:
                        uow.app_settings.set(ANALYSIS_ENABLED_KEY, "false")
                        waiting = uow.events.list_by_status(
                            EventProcessingStatus.AI_PROCESSING,
                            limit=_CANCEL_BATCH_LIMIT,
                        )
                        for event in waiting:
                            event.cancel_ai_processing()
                            uow.events.update(event)
                        cancelled = len(waiting)
                    uow.commit()
                    return cancelled

            return run_mutating(_run)


class GetAIOutputTokenLimitUseCase:
    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], *, configured_default: int
    ) -> None:
        self._uow_factory = uow_factory
        self._configured_default = configured_default

    def execute(self) -> AIOutputTokenLimitDto:
        with (
            use_case_scope("GetAIOutputTokenLimit"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            return _limit_dto(uow, self._configured_default)


class SetAIOutputTokenLimitUseCase:
    """Save an override, or pass ``None`` to go back to the configured default."""

    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], *, configured_default: int
    ) -> None:
        self._uow_factory = uow_factory
        self._configured_default = configured_default

    def execute(self, value: int | None) -> AIOutputTokenLimitDto:
        with use_case_scope("SetAIOutputTokenLimit"):
            if value is not None and not (
                MIN_OUTPUT_TOKENS <= value <= MAX_OUTPUT_TOKENS
            ):
                raise ApplicationValidationError(
                    f"AI output token limit must be between {MIN_OUTPUT_TOKENS} "
                    f"and {MAX_OUTPUT_TOKENS}."
                )

            def _run() -> AIOutputTokenLimitDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    if value is None:
                        uow.app_settings.delete(MAX_OUTPUT_TOKENS_KEY)
                    else:
                        uow.app_settings.set(MAX_OUTPUT_TOKENS_KEY, str(value))
                    uow.commit()
                    return _limit_dto(uow, self._configured_default)

            return run_mutating(_run)


def _limit_dto(uow: UnitOfWork, configured_default: int) -> AIOutputTokenLimitDto:
    return AIOutputTokenLimitDto(
        effective=effective_max_output_tokens(uow, configured_default),
        configured_default=configured_default,
        overridden=uow.app_settings.get(MAX_OUTPUT_TOKENS_KEY) is not None,
        minimum=MIN_OUTPUT_TOKENS,
        maximum=MAX_OUTPUT_TOKENS,
    )
