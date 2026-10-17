"""AWS Bedrock adapter for the provider-neutral ``AIProvider`` port.

boto3/botocore are imported only here (and in ``infrastructure/ai/errors.py``)
per the architecture guard tests. AWS credentials are resolved via boto3's
default credential chain and are never read, stored, or logged by this
adapter — only event/model/latency/success metadata is logged, never the
prompt or the raw response text (see spec privacy requirements).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from insightflow.application.exceptions.ai import AIProviderInvalidResponseError
from insightflow.application.ports.ai import AIAnalysisRequest, AIAnalysisResponse
from insightflow.infrastructure.ai.errors import raise_translated_bedrock_error

logger = logging.getLogger("insightflow.infrastructure.ai")

_CONNECT_TIMEOUT_SECONDS = 10.0


class BedrockAIProvider:
    """``AIProvider`` implementation backed by the Bedrock Converse API."""

    def __init__(
        self,
        *,
        model_id: str,
        region: str | None,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            config = Config(
                read_timeout=self._timeout_seconds,
                connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                retries={"max_attempts": self._max_retries, "mode": "standard"},
            )
            self._client = boto3.client(
                "bedrock-runtime", region_name=self._region, config=config
            )
        return self._client

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        client = self._get_client()
        try:
            result: Any = client.converse(
                modelId=self._model_id,
                system=[{"text": request.system_instructions}],
                messages=[
                    {"role": "user", "content": [{"text": request.user_content}]}
                ],
                inferenceConfig={
                    "maxTokens": request.max_output_tokens,
                    "temperature": request.temperature,
                },
            )
        except (ClientError, BotoCoreError) as exc:
            raise_translated_bedrock_error(exc)

        event_id = request.metadata.get("event_id", "unknown")
        usage = result.get("usage", {})
        logger.info(
            "Bedrock analyze succeeded event_id=%s model=%s input_tokens=%s "
            "output_tokens=%s",
            event_id,
            self._model_id,
            usage.get("inputTokens"),
            usage.get("outputTokens"),
        )

        if result.get("stopReason") == "max_tokens":
            raise AIProviderInvalidResponseError(
                "AI response was cut off at the output token limit "
                f"({request.max_output_tokens}); raise "
                "INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS."
            )
        text = _extract_text(result)
        payload = _parse_json_object(text)
        return _payload_to_response(payload)


def _extract_text(result: Any) -> str:
    try:
        blocks = result["output"]["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise AIProviderInvalidResponseError(
            "Bedrock response did not contain a message."
        ) from exc
    return "".join(block.get("text", "") for block in blocks if isinstance(block, dict))


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict):
        start = text.find("{")
        end = text.rfind("}")
        parsed = None
        if start != -1 and end != -1 and end > start:
            try:
                candidate = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                candidate = None
            if isinstance(candidate, dict):
                parsed = candidate
    if not isinstance(parsed, dict):
        raise AIProviderInvalidResponseError("Bedrock response was not valid JSON.")
    return parsed


def _payload_to_response(payload: dict[str, Any]) -> AIAnalysisResponse:
    try:
        return AIAnalysisResponse(
            summary=_optional_str(payload.get("concise_summary")),
            key_points=_str_tuple(payload.get("key_points")),
            why_it_matters=_optional_str(payload.get("why_it_matters")),
            what_to_watch=_str_tuple(payload.get("what_to_watch")),
            sentiment=_optional_str(payload.get("sentiment")),
            market_impact_direction=_optional_str(
                payload.get("market_impact_direction")
            ),
            market_impact_score=_optional_float(payload.get("market_impact_score")),
            market_impact_relevance=_optional_str(
                payload.get("market_impact_relevance")
            ),
            market_impact_reasoning=_optional_str(
                payload.get("market_impact_reasoning")
            ),
            market_impact_affected_assets=_str_tuple(
                payload.get("market_impact_affected_assets")
            ),
            confidence=_optional_float(payload.get("confidence")),
            entities=_str_tuple(payload.get("entities")),
            provider_metadata={},
            generated_content=_optional_str(payload.get("generated_content")),
        )
    except (TypeError, ValueError) as exc:
        raise AIProviderInvalidResponseError(
            f"Bedrock response JSON had an unexpected shape: {exc}"
        ) from exc


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AIProviderInvalidResponseError("Expected a JSON array of strings.")
    return tuple(str(item) for item in value)
