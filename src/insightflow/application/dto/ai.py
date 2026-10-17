"""AI worker job DTO (Phase 11)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIAnalysisJob:
    """One unit of work for the AI worker.

    ``ai_profile_id``/``profile_version`` are ``None`` for automatic
    dispatch (the event's topic's configured profile is used); manual
    reprocessing may pin an explicit profile/version.
    """

    event_id: str
    ai_profile_id: str | None = None
    profile_version: int | None = None
    # True when the user asked for it (Analyze / Re-analyze): it runs even
    # while automatic AI analysis is turned off.
    manual: bool = False


@dataclass(frozen=True, slots=True)
class AIOutputTokenLimitDto:
    """The AI output token limit the next analysis will use."""

    effective: int
    configured_default: int  # from INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS / .env
    overridden: bool  # True when set from the Settings page
    minimum: int
    maximum: int
