"""Market impact value object."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.domain.enums import MarketImpactDirection
from insightflow.domain.value_objects._guards import require_non_empty
from insightflow.domain.value_objects.primitives import Confidence


@dataclass(frozen=True, slots=True)
class MarketImpact:
    """Optional market interpretation produced by AI analysis.

    This is interpretive guidance, not a guaranteed prediction.
    """

    relevance: str
    direction: MarketImpactDirection
    affected_assets: tuple[str, ...]
    reasoning: str
    confidence: Confidence

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "relevance", require_non_empty(self.relevance, "relevance")
        )
        object.__setattr__(
            self, "reasoning", require_non_empty(self.reasoning, "reasoning")
        )
        cleaned_assets = tuple(
            require_non_empty(asset, "affected_assets item")
            for asset in self.affected_assets
        )
        object.__setattr__(self, "affected_assets", cleaned_assets)
