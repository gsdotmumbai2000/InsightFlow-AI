"""Validates provider-neutral AI responses against domain rules (Phase 11).

Reuses existing domain constructors (``Sentiment``, ``MarketImpactDirection``,
``Confidence``, ``MarketImpact``) as the single source of validation truth
instead of re-implementing range/enum checks. Invalid AI output must never
be silently coerced into fabricated defaults — every failure raises
``AIResponseValidationError``.
"""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.application.exceptions.ai import AIResponseValidationError
from insightflow.application.ports.ai import AIAnalysisResponse
from insightflow.domain import (
    AIOutputStyle,
    Confidence,
    MarketImpact,
    MarketImpactDirection,
    Sentiment,
)
from insightflow.domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class ValidatedAIResult:
    """Analysis fields ready to pass to ``AIAnalysis.create``."""

    summary: str
    why_it_matters: str | None
    key_facts: tuple[str, ...]
    what_to_watch: tuple[str, ...]
    entities: tuple[str, ...]
    sentiment: Sentiment | None
    confidence: Confidence | None
    market_impact: MarketImpact | None
    generated_content: str | None = None


_FALLBACK_SUMMARY_CHARS = 200


class AIResponseValidator:
    """Validates an ``AIAnalysisResponse`` before it may be persisted."""

    def validate(
        self,
        response: AIAnalysisResponse,
        *,
        output_style: AIOutputStyle = AIOutputStyle.ANALYSIS,
    ) -> ValidatedAIResult:
        if output_style is AIOutputStyle.CUSTOM_TEXT:
            return self._validate_custom_text(response)
        summary = (response.summary or "").strip()
        if not summary:
            raise AIResponseValidationError(
                "AI response is missing a non-empty summary."
            )

        key_facts = self._non_empty_strings(response.key_points, "key_points")
        what_to_watch = self._non_empty_strings(response.what_to_watch, "what_to_watch")
        entities = self._non_empty_strings(response.entities, "entities")
        why_it_matters = (response.why_it_matters or "").strip() or None

        sentiment = self._validate_sentiment(response.sentiment)
        confidence = self._validate_confidence(response.confidence)
        market_impact = self._validate_market_impact(response)

        return ValidatedAIResult(
            summary=summary,
            why_it_matters=why_it_matters,
            key_facts=key_facts,
            what_to_watch=what_to_watch,
            entities=entities,
            sentiment=sentiment,
            confidence=confidence,
            market_impact=market_impact,
        )

    def _validate_custom_text(self, response: AIAnalysisResponse) -> ValidatedAIResult:
        """The requested text is required; the analysis fields are not asked for."""
        content = (response.generated_content or "").strip()
        if not content:
            raise AIResponseValidationError(
                "AI response is missing the requested generated_content."
            )
        # The summary only labels the event in lists, so a missing one is
        # derived from the text rather than failing the whole result.
        summary = (response.summary or "").strip() or _first_chars(
            content, _FALLBACK_SUMMARY_CHARS
        )
        return ValidatedAIResult(
            summary=summary,
            why_it_matters=None,
            key_facts=(),
            what_to_watch=(),
            entities=self._non_empty_strings(response.entities, "entities"),
            sentiment=None,
            confidence=None,
            market_impact=None,
            generated_content=content,
        )

    @staticmethod
    def _non_empty_strings(items: tuple[str, ...], field_name: str) -> tuple[str, ...]:
        if not isinstance(items, tuple | list):
            raise AIResponseValidationError(f"{field_name} must be a list of strings.")
        cleaned: list[str] = []
        for item in items:
            if not isinstance(item, str) or not item.strip():
                raise AIResponseValidationError(
                    f"{field_name} must only contain non-empty strings."
                )
            cleaned.append(item.strip())
        return tuple(cleaned)

    @staticmethod
    def _validate_sentiment(raw: str | None) -> Sentiment | None:
        if raw is None:
            return None
        try:
            return Sentiment(raw.strip().upper())
        except (ValueError, AttributeError) as exc:
            raise AIResponseValidationError(f"Invalid sentiment: {raw!r}.") from exc

    @staticmethod
    def _validate_confidence(raw: float | None) -> Confidence | None:
        if raw is None:
            return None
        try:
            return Confidence(float(raw))
        except (TypeError, ValueError, DomainValidationError) as exc:
            raise AIResponseValidationError(f"Invalid confidence: {raw!r}.") from exc

    @staticmethod
    def _validate_market_impact(response: AIAnalysisResponse) -> MarketImpact | None:
        direction_raw = _blank_to_none(response.market_impact_direction)
        details = (
            response.market_impact_score,
            _blank_to_none(response.market_impact_relevance),
            _blank_to_none(response.market_impact_reasoning),
        )
        no_details = all(value is None for value in details)
        if direction_raw is None and no_details:
            return None
        # The schema offers NOT_APPLICABLE as a direction, and models
        # reasonably pair it with null details for non-market content. That
        # is an explicit "no assessment", not a partial one.
        if (
            no_details
            and direction_raw is not None
            and direction_raw.strip().upper()
            == MarketImpactDirection.NOT_APPLICABLE.value
        ):
            return None
        if direction_raw is None or any(value is None for value in details):
            raise AIResponseValidationError(
                "Market impact requires direction, score, relevance, and "
                "reasoning together, or none of them."
            )
        try:
            direction = MarketImpactDirection(
                str(response.market_impact_direction).strip().upper()
            )
            score_confidence = Confidence(float(response.market_impact_score))  # type: ignore[arg-type]
            return MarketImpact(
                relevance=str(response.market_impact_relevance),
                direction=direction,
                affected_assets=tuple(response.market_impact_affected_assets),
                reasoning=str(response.market_impact_reasoning),
                confidence=score_confidence,
            )
        except (ValueError, TypeError, DomainValidationError) as exc:
            raise AIResponseValidationError(f"Invalid market impact: {exc}") from exc


def _first_chars(text: str, limit: int) -> str:
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= limit:
        return first_line
    return first_line[:limit].rstrip() + "…"


def _blank_to_none(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value
