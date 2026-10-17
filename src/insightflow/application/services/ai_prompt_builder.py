"""Provider-neutral AI prompt construction (Phase 11).

Building the instructions that go to an AI provider is application-layer
policy, not provider adapter code — this module has no knowledge of
Bedrock/OpenAI/Anthropic/Gemini and produces only the plain
``AIAnalysisRequest`` defined in ``application/ports/ai.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.application.ports.ai import AIAnalysisRequest
from insightflow.domain import AIOutputStyle, AIProfile, IntelligenceEvent

_RESPONSE_SCHEMA_INSTRUCTIONS = """
Respond with a single JSON object and nothing else — no markdown fences, no
prose before or after it. Use exactly these keys:

{
  "concise_summary": "<one or two factual sentences>",
  "key_points": ["<short factual point>", "..."],
  "why_it_matters": "<why this may matter to someone tracking this topic, or null>",
  "what_to_watch": ["<a concrete thing to watch next>", "..."],
  "sentiment": "<POSITIVE, NEGATIVE, NEUTRAL, MIXED, UNCERTAIN, or NOT_APPLICABLE>",
  "market_impact_direction": "<BULLISH, BEARISH, MIXED, UNCERTAIN, or null>",
  "market_impact_score": "<0.0-1.0 magnitude of the potential impact, or null>",
  "market_impact_relevance": "<short label of what this could affect, or null>",
  "market_impact_reasoning": "<one or two sentences of reasoning, or null>",
  "market_impact_affected_assets": ["<asset or market>", "..."],
  "confidence": "<0.0-1.0, how confident you are in this analysis>",
  "entities": ["<person, organization, or thing mentioned>", "..."]
}

Provide all four of market_impact_direction, market_impact_score,
market_impact_relevance, and market_impact_reasoning together. If a
market-impact assessment does not apply to this content, set all four to
null (not NOT_APPLICABLE) and market_impact_affected_assets to [].
""".strip()

_SAFETY_INSTRUCTIONS = """
You are an analysis assistant, not a financial advisor. Follow these rules
strictly:
- Distinguish clearly stated facts from your own interpretation.
- Do not invent facts, numbers, or details that are not present in the
  source content. If information is missing, say so instead of guessing.
- Do not claim certainty the source content does not support; reflect
  genuine uncertainty in "confidence" and in your wording.
- Any market impact assessment is your own interpretive judgment, not a
  guaranteed prediction and not financial advice.
- Never output trading orders, position sizes, or instructions such as
  "buy", "sell", "short", or specific instrument/strike recommendations.
""".strip()

_CUSTOM_TEXT_SCHEMA_INSTRUCTIONS = """
Respond with a single JSON object and nothing else — no markdown fences, no
prose before or after it. Use exactly these keys:

{
  "generated_content": "<exactly the text the instructions above ask for,
    in the language, style, and format they ask for>",
  "concise_summary": "<one short English sentence describing the source content>",
  "entities": ["<person, organization, or place mentioned>", "..."]
}

Put everything the instructions ask you to write into "generated_content",
using \\n for line breaks inside the JSON string. Do not add analysis,
sentiment, or market commentary the instructions do not ask for.
""".strip()

_CUSTOM_TEXT_SAFETY_INSTRUCTIONS = """
Follow these rules strictly:
- Base the text only on the source content. Do not invent facts, numbers,
  quotes, or details that are not present in it.
- If the source content does not contain enough information for what the
  instructions ask, write only what it supports.
""".strip()

DEFAULT_MAX_INPUT_CHARS = 12_000


@dataclass(frozen=True, slots=True)
class AIPromptBuilder:
    """Builds a provider-neutral ``AIAnalysisRequest`` from domain data."""

    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS

    def build(
        self,
        *,
        event: IntelligenceEvent,
        profile: AIProfile,
        topic_name: str | None,
        max_output_tokens: int,
        temperature: float,
    ) -> AIAnalysisRequest:
        if profile.output_style is AIOutputStyle.CUSTOM_TEXT:
            safety, schema = (
                _CUSTOM_TEXT_SAFETY_INSTRUCTIONS,
                _CUSTOM_TEXT_SCHEMA_INSTRUCTIONS,
            )
        else:
            safety, schema = _SAFETY_INSTRUCTIONS, _RESPONSE_SCHEMA_INSTRUCTIONS
        system_instructions = "\n\n".join(
            (profile.instructions.strip(), safety, schema)
        )
        content = self._truncate(event.normalized_content or "")
        user_content_lines = [
            f"Topic: {topic_name}" if topic_name else "Topic: (unspecified)",
            f"Title: {event.title}" if event.title else "Title: (none)",
            "Content:",
            content or "(no content available)",
        ]
        return AIAnalysisRequest(
            system_instructions=system_instructions,
            user_content="\n".join(user_content_lines),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            metadata={"event_id": event.id.value},
        )

    def _truncate(self, content: str) -> str:
        if len(content) <= self.max_input_chars:
            return content
        return content[: self.max_input_chars] + "\n[content truncated]"
