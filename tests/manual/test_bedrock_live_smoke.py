"""Manual AWS Bedrock smoke test (Phase 11).

NOT part of the normal test suite. Requires real AWS credentials, a real
network call, and incurs real cost — skipped unless explicitly opted into
via ``INSIGHTFLOW_RUN_REAL_AI_TESTS=1``. Run directly with:

    INSIGHTFLOW_RUN_REAL_AI_TESTS=1 pytest tests/manual/test_bedrock_live_smoke.py -s

Configure the model/region via the same ``INSIGHTFLOW_AI_*`` environment
variables used by the application (see ``.env.example``), and ensure AWS
credentials are resolvable via boto3's default credential chain.
"""

from __future__ import annotations

import os

import pytest

from insightflow.application.ports.ai import AIAnalysisRequest
from insightflow.infrastructure.ai.bedrock_adapter import BedrockAIProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("INSIGHTFLOW_RUN_REAL_AI_TESTS") != "1",
    reason="Real AWS Bedrock smoke test; set INSIGHTFLOW_RUN_REAL_AI_TESTS=1 to run.",
)


def test_bedrock_analyze_real_call() -> None:
    provider = BedrockAIProvider(
        model_id=os.environ.get(
            "INSIGHTFLOW_AI_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ),
        region=os.environ.get("INSIGHTFLOW_AI_REGION"),
        timeout_seconds=30.0,
        max_retries=1,
    )
    request = AIAnalysisRequest(
        system_instructions=(
            "You are an analysis assistant. Respond with a single JSON object "
            'with keys "concise_summary" (string), "key_points" (array of '
            'strings), "why_it_matters" (string or null), "what_to_watch" '
            '(array of strings), "sentiment" (one of POSITIVE, NEGATIVE, '
            "NEUTRAL, MIXED, UNCERTAIN, NOT_APPLICABLE), "
            '"market_impact_direction" (null), "market_impact_score" (null), '
            '"market_impact_relevance" (null), "market_impact_reasoning" '
            '(null), "market_impact_affected_assets" (empty array), '
            '"confidence" (0.0-1.0), "entities" (array of strings). No other '
            "text."
        ),
        user_content=(
            "Topic: TEST\nTitle: Smoke test\nContent: A quiet Tuesday; "
            "nothing of note happened."
        ),
        max_output_tokens=512,
        temperature=0.0,
        metadata={"event_id": "manual-smoke-test"},
    )
    response = provider.analyze(request)
    assert response.summary
    print("Bedrock smoke test response:", response)
