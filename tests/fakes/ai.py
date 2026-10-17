"""In-memory fake AI provider for tests (no network, no provider SDK)."""

from __future__ import annotations

from dataclasses import dataclass, field

from insightflow.application.exceptions.ai import AIProviderError
from insightflow.application.ports.ai import AIAnalysisRequest, AIAnalysisResponse


def make_response(
    *,
    summary: str = "A test event summary.",
    key_points: tuple[str, ...] = ("Point one.",),
    why_it_matters: str | None = "It matters for testing.",
    what_to_watch: tuple[str, ...] = ("Watch this.",),
    sentiment: str | None = "NEUTRAL",
    market_impact_direction: str | None = None,
    market_impact_score: float | None = None,
    market_impact_relevance: str | None = None,
    market_impact_reasoning: str | None = None,
    market_impact_affected_assets: tuple[str, ...] = (),
    confidence: float | None = 0.5,
    entities: tuple[str, ...] = ("Example Corp",),
    generated_content: str | None = None,
) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        generated_content=generated_content,
        summary=summary,
        key_points=key_points,
        why_it_matters=why_it_matters,
        what_to_watch=what_to_watch,
        sentiment=sentiment,
        market_impact_direction=market_impact_direction,
        market_impact_score=market_impact_score,
        market_impact_relevance=market_impact_relevance,
        market_impact_reasoning=market_impact_reasoning,
        market_impact_affected_assets=market_impact_affected_assets,
        confidence=confidence,
        entities=entities,
    )


@dataclass
class FakeAIProvider:
    """Configurable test double for ``AIProvider``."""

    response: AIAnalysisResponse = field(default_factory=make_response)
    error: AIProviderError | None = None
    requests: list[AIAnalysisRequest] = field(default_factory=list)

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response
