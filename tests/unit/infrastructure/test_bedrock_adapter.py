"""BedrockAIProvider tests (Phase 11) — fully offline via botocore Stubber.

No real AWS credentials or network calls. Provider translation of
success/error responses is exercised directly against a stubbed
``bedrock-runtime`` client.
"""

from __future__ import annotations

import json
from typing import Any

import boto3
import pytest
from botocore.stub import Stubber

from insightflow.application.exceptions.ai import (
    AIProviderAuthenticationError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from insightflow.application.ports.ai import AIAnalysisRequest
from insightflow.infrastructure.ai.bedrock_adapter import BedrockAIProvider


def _request() -> AIAnalysisRequest:
    return AIAnalysisRequest(
        system_instructions="Summarize.",
        user_content="Something happened.",
        max_output_tokens=256,
        temperature=0.2,
        metadata={"event_id": "evt-1"},
    )


def _converse_response(text: str) -> dict[str, Any]:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
        "metrics": {"latencyMs": 5},
    }


def _provider_with_stubbed_client() -> tuple[BedrockAIProvider, Stubber]:
    provider = BedrockAIProvider(
        model_id="fake-model", region="us-east-1", timeout_seconds=5.0, max_retries=0
    )
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    stubber = Stubber(client)
    provider._client = client  # test seam: inject the stubbed client directly
    return provider, stubber


def test_analyze_success_maps_payload() -> None:
    provider, stubber = _provider_with_stubbed_client()
    payload = {
        "concise_summary": "Summary.",
        "key_points": ["Point"],
        "why_it_matters": "Matters.",
        "what_to_watch": ["Watch"],
        "sentiment": "NEUTRAL",
        "market_impact_direction": None,
        "market_impact_score": None,
        "market_impact_relevance": None,
        "market_impact_reasoning": None,
        "market_impact_affected_assets": [],
        "confidence": 0.5,
        "entities": ["Corp"],
    }
    stubber.add_response("converse", _converse_response(json.dumps(payload)))
    with stubber:
        response = provider.analyze(_request())
    assert response.summary == "Summary."
    assert response.entities == ("Corp",)
    assert response.confidence == 0.5


def test_analyze_malformed_json_raises_invalid_response() -> None:
    provider, stubber = _provider_with_stubbed_client()
    stubber.add_response("converse", _converse_response("not json at all"))
    with stubber, pytest.raises(AIProviderInvalidResponseError):
        provider.analyze(_request())


def test_analyze_maps_generated_content() -> None:
    provider, stubber = _provider_with_stubbed_client()
    payload = {
        "generated_content": "தமிழ் செய்தி\nவரி 2",
        "concise_summary": "CM Vijay meets Naidu.",
        "entities": ["Vijay"],
    }
    stubber.add_response(
        "converse", _converse_response(json.dumps(payload, ensure_ascii=False))
    )
    with stubber:
        response = provider.analyze(_request())
    assert response.generated_content == "தமிழ் செய்தி\nவரி 2"
    assert response.summary == "CM Vijay meets Naidu."


def test_analyze_truncated_output_names_the_token_limit() -> None:
    provider, stubber = _provider_with_stubbed_client()
    truncated = _converse_response('{"concise_summary": "Cut off mid')
    truncated["stopReason"] = "max_tokens"
    stubber.add_response("converse", truncated)
    with stubber, pytest.raises(AIProviderInvalidResponseError, match="token limit"):
        provider.analyze(_request())


def test_analyze_throttling_raises_rate_limit_error() -> None:
    provider, stubber = _provider_with_stubbed_client()
    stubber.add_client_error(
        "converse", service_error_code="ThrottlingException", http_status_code=429
    )
    with stubber, pytest.raises(AIProviderRateLimitError):
        provider.analyze(_request())


def test_analyze_access_denied_raises_authentication_error() -> None:
    provider, stubber = _provider_with_stubbed_client()
    stubber.add_client_error(
        "converse", service_error_code="AccessDeniedException", http_status_code=403
    )
    with stubber, pytest.raises(AIProviderAuthenticationError):
        provider.analyze(_request())


def test_translate_read_timeout_raises_timeout_error() -> None:
    from botocore.exceptions import ReadTimeoutError

    from insightflow.infrastructure.ai.errors import raise_translated_bedrock_error

    with pytest.raises(AIProviderTimeoutError):
        try:
            raise ReadTimeoutError(endpoint_url="https://bedrock-runtime")
        except ReadTimeoutError as exc:
            raise_translated_bedrock_error(exc)
