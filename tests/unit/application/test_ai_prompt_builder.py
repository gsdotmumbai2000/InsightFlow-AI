"""AIPromptBuilder tests (Phase 11)."""

from __future__ import annotations

from datetime import UTC, datetime

from insightflow.application.services.ai_prompt_builder import AIPromptBuilder
from insightflow.domain import AIProfile, IntelligenceEvent, SourceReference, SourceType


def _event(content: str | None, *, title: str | None = "A title") -> IntelligenceEvent:
    return IntelligenceEvent.create(
        source=SourceReference(
            source_type=SourceType.GENERIC, source_id="src", external_id="ext-1"
        ),
        title=title,
        normalized_content=content,
        received_at=datetime.now(UTC),
    )


def _profile(instructions: str = "Summarize the event.") -> AIProfile:
    return AIProfile.create(
        name="Default", instructions=instructions, output_schema_version="v1"
    )


def test_build_includes_profile_instructions_and_content() -> None:
    builder = AIPromptBuilder()
    request = builder.build(
        event=_event("Full body text."),
        profile=_profile("Focus on market impact."),
        topic_name="TRUMP",
        max_output_tokens=256,
        temperature=0.1,
    )
    assert "Focus on market impact." in request.system_instructions
    assert "distinguish" in request.system_instructions.lower()
    assert "trading" in request.system_instructions.lower()
    assert "Topic: TRUMP" in request.user_content
    assert "Full body text." in request.user_content
    assert request.max_output_tokens == 256
    assert request.temperature == 0.1
    assert request.metadata["event_id"]


def test_build_handles_missing_content_and_topic() -> None:
    builder = AIPromptBuilder()
    request = builder.build(
        event=_event(None, title=None),
        profile=_profile(),
        topic_name=None,
        max_output_tokens=256,
        temperature=0.1,
    )
    assert "Topic: (unspecified)" in request.user_content
    assert "no content available" in request.user_content


def test_build_truncates_long_content() -> None:
    builder = AIPromptBuilder(max_input_chars=10)
    request = builder.build(
        event=_event("x" * 100),
        profile=_profile(),
        topic_name=None,
        max_output_tokens=256,
        temperature=0.1,
    )
    assert "[content truncated]" in request.user_content
    assert "x" * 100 not in request.user_content
