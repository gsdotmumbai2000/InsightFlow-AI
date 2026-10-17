"""Provider-neutral AI analysis port (Phase 11).

No provider SDK type (boto3, OpenAI, Anthropic, Gemini, ...) may appear on
this boundary — ``AIAnalysisRequest``/``AIAnalysisResponse`` are plain,
provider-agnostic dataclasses. Infrastructure adapters (``infrastructure/ai``)
translate to/from whatever a specific provider's SDK requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AIAnalysisRequest:
    """Everything a provider needs to analyze one event, and nothing else."""

    system_instructions: str
    user_content: str
    max_output_tokens: int
    temperature: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AIAnalysisResponse:
    """Provider-neutral structured analysis result, pre-domain-validation.

    Fields mirror the JSON schema requested by ``AIPromptBuilder``. All
    fields are optional at this boundary — semantic validation (required
    fields, enum membership, numeric ranges) happens in
    ``AIResponseValidator``, not here.
    """

    summary: str | None
    key_points: tuple[str, ...]
    why_it_matters: str | None
    what_to_watch: tuple[str, ...]
    sentiment: str | None
    market_impact_direction: str | None
    market_impact_score: float | None
    market_impact_relevance: str | None
    market_impact_reasoning: str | None
    market_impact_affected_assets: tuple[str, ...]
    confidence: float | None
    entities: tuple[str, ...]
    provider_metadata: dict[str, str] = field(default_factory=dict)
    # Only requested for CUSTOM_TEXT profiles (see AIPromptBuilder).
    generated_content: str | None = None


@runtime_checkable
class AIProvider(Protocol):
    """Provider-neutral AI analysis boundary."""

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """Analyze one event. Raises ``AIProviderError`` subclasses on failure."""
