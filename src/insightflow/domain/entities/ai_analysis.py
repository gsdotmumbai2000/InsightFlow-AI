"""AIAnalysis entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from insightflow.domain.enums import AIAnalysisStatus, Priority, Sentiment
from insightflow.domain.exceptions import (
    DomainValidationError,
    InvalidStateTransitionError,
)
from insightflow.domain.value_objects import (
    AIAnalysisId,
    AIProfileId,
    Confidence,
    EventId,
    MarketImpact,
)
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class AIAnalysis:
    """Validated AI result distinguishing facts from interpretation."""

    id: AIAnalysisId
    event_id: EventId
    profile_id: AIProfileId
    profile_version: int
    provider: str
    model: str
    summary: str
    why_it_matters: str | None
    key_facts: tuple[str, ...]
    what_to_watch: tuple[str, ...]
    market_impact: MarketImpact | None
    entities: tuple[str, ...]
    sentiment: Sentiment | None
    confidence: Confidence | None
    status: AIAnalysisStatus
    created_at: datetime
    updated_at: datetime
    priority: Priority | None = None
    latency_ms: int | None = None
    failure_reason: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.provider = require_non_empty(self.provider, "provider")
        self.model = require_non_empty(self.model, "model")
        if not isinstance(self.profile_version, int) or isinstance(
            self.profile_version, bool
        ):
            raise DomainValidationError("profile_version must be an integer.")
        if self.profile_version < 1:
            raise DomainValidationError("profile_version must be >= 1.")
        if self.status is AIAnalysisStatus.COMPLETED or self.summary.strip():
            self.summary = require_non_empty(self.summary, "summary")
        else:
            self.summary = ""
        if self.why_it_matters is not None:
            self.why_it_matters = require_non_empty(
                self.why_it_matters, "why_it_matters"
            )
        self.key_facts = tuple(
            require_non_empty(item, "key_facts item") for item in self.key_facts
        )
        self.what_to_watch = tuple(
            require_non_empty(item, "what_to_watch item") for item in self.what_to_watch
        )
        self.entities = tuple(
            require_non_empty(item, "entities item") for item in self.entities
        )
        if self.latency_ms is not None and self.latency_ms < 0:
            raise DomainValidationError("latency_ms cannot be negative.")
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        event_id: EventId,
        profile_id: AIProfileId,
        profile_version: int,
        provider: str,
        model: str,
        summary: str = "",
        why_it_matters: str | None = None,
        key_facts: tuple[str, ...] | list[str] = (),
        what_to_watch: tuple[str, ...] | list[str] = (),
        market_impact: MarketImpact | None = None,
        entities: tuple[str, ...] | list[str] = (),
        sentiment: Sentiment | None = None,
        confidence: Confidence | None = None,
        priority: Priority | None = None,
        latency_ms: int | None = None,
        analysis_id: AIAnalysisId | None = None,
        created_at: datetime | None = None,
    ) -> AIAnalysis:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=analysis_id or AIAnalysisId.generate(),
            event_id=event_id,
            profile_id=profile_id,
            profile_version=profile_version,
            provider=provider,
            model=model,
            summary=summary,
            why_it_matters=why_it_matters,
            key_facts=tuple(key_facts),
            what_to_watch=tuple(what_to_watch),
            market_impact=market_impact,
            entities=tuple(entities),
            sentiment=sentiment,
            confidence=confidence,
            status=AIAnalysisStatus.PENDING,
            priority=priority,
            latency_ms=latency_ms,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def mark_completed(
        self,
        *,
        summary: str | None = None,
        at: datetime | None = None,
    ) -> None:
        if self.status is AIAnalysisStatus.FAILED:
            raise InvalidStateTransitionError(
                "Cannot mark a failed AI analysis as completed."
            )
        if summary is not None:
            self.summary = require_non_empty(summary, "summary")
        else:
            self.summary = require_non_empty(self.summary, "summary")
        self.status = AIAnalysisStatus.COMPLETED
        self.failure_reason = None
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_failed(self, *, reason: str, at: datetime | None = None) -> None:
        if self.status is AIAnalysisStatus.COMPLETED:
            raise InvalidStateTransitionError(
                "Cannot mark a completed AI analysis as failed."
            )
        self.status = AIAnalysisStatus.FAILED
        self.failure_reason = require_non_empty(reason, "reason")
        self.updated_at = require_aware_utc(at or utc_now(), "at")
