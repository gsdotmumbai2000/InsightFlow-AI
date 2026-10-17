"""AIResponseValidator tests (Phase 11)."""

from __future__ import annotations

import pytest
from tests.fakes.ai import make_response

from insightflow.application.exceptions.ai import AIResponseValidationError
from insightflow.application.services.ai_response_validator import (
    AIResponseValidator,
)
from insightflow.domain import MarketImpactDirection, Sentiment


def test_validate_success_maps_domain_types() -> None:
    validator = AIResponseValidator()
    response = make_response(
        summary="Concise.",
        sentiment="positive",
        confidence=0.9,
        market_impact_direction="bullish",
        market_impact_score=0.6,
        market_impact_relevance="equities",
        market_impact_reasoning="Reasoning.",
        market_impact_affected_assets=("NIFTY",),
    )
    result = validator.validate(response)
    assert result.summary == "Concise."
    assert result.sentiment is Sentiment.POSITIVE
    assert result.confidence is not None and result.confidence.value == 0.9
    assert result.market_impact is not None
    assert result.market_impact.direction is MarketImpactDirection.BULLISH
    assert result.market_impact.confidence.value == 0.6


def test_validate_rejects_empty_summary() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(make_response(summary=""))


def test_validate_rejects_invalid_sentiment() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(make_response(sentiment="VERY_HAPPY"))


def test_validate_rejects_out_of_range_confidence() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(make_response(confidence=1.5))


def test_validate_rejects_partial_market_impact() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(make_response(market_impact_direction="BULLISH"))


def test_validate_allows_absent_market_impact() -> None:
    validator = AIResponseValidator()
    result = validator.validate(make_response())
    assert result.market_impact is None


def test_validate_treats_not_applicable_without_details_as_absent() -> None:
    """Non-market content (e.g. regional politics): the model answers
    NOT_APPLICABLE with null details — a clear "no assessment"."""
    validator = AIResponseValidator()
    result = validator.validate(make_response(market_impact_direction="NOT_APPLICABLE"))
    assert result.market_impact is None


def test_validate_treats_blank_market_impact_fields_as_absent() -> None:
    validator = AIResponseValidator()
    result = validator.validate(
        make_response(
            market_impact_direction=" ",
            market_impact_relevance="",
            market_impact_reasoning="",
        )
    )
    assert result.market_impact is None


def test_validate_rejects_not_applicable_with_partial_details() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(
            make_response(
                market_impact_direction="NOT_APPLICABLE",
                market_impact_reasoning="Not market related.",
            )
        )


def test_validate_rejects_non_string_list_items() -> None:
    validator = AIResponseValidator()
    with pytest.raises(AIResponseValidationError):
        validator.validate(make_response(key_points=("",)))
