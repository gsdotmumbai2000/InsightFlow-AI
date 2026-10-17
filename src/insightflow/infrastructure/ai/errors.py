"""Translate AWS Bedrock / botocore errors into application AI errors.

boto3/botocore types never leak past this module — everything else in the
application only ever sees ``AIProviderError`` subclasses.
"""

from __future__ import annotations

import logging
from typing import NoReturn

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)

from insightflow.application.exceptions.ai import (
    AIProviderAuthenticationError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

logger = logging.getLogger("insightflow.infrastructure.ai")

_AUTH_ERROR_CODES = frozenset(
    {
        "AccessDeniedException",
        "UnrecognizedClientException",
        "ExpiredTokenException",
        "UnauthorizedException",
    }
)
_RATE_LIMIT_ERROR_CODES = frozenset({"ThrottlingException", "TooManyRequestsException"})
_UNAVAILABLE_ERROR_CODES = frozenset(
    {
        "ModelNotReadyException",
        "ModelTimeoutException",
        "ServiceUnavailableException",
        "ServiceQuotaExceededException",
        "InternalServerException",
    }
)


def translate_bedrock_error(exc: BaseException) -> AIProviderError:
    """Map a boto3/botocore/network exception to an ``AIProviderError``."""
    name = type(exc).__name__
    logger.warning("Bedrock infrastructure error category=%s", name)

    if isinstance(exc, ReadTimeoutError | ConnectTimeoutError):
        return AIProviderTimeoutError("AWS Bedrock request timed out.")
    if isinstance(exc, NoCredentialsError):
        return AIProviderAuthenticationError("AWS credentials are not available.")
    if isinstance(exc, EndpointConnectionError):
        return AIProviderUnavailableError("Could not reach the AWS Bedrock endpoint.")
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in _AUTH_ERROR_CODES:
            return AIProviderAuthenticationError(
                "AWS Bedrock rejected the request's credentials or authorization."
            )
        if code in _RATE_LIMIT_ERROR_CODES:
            return AIProviderRateLimitError("AWS Bedrock throttled the request.")
        if code in _UNAVAILABLE_ERROR_CODES:
            return AIProviderUnavailableError("AWS Bedrock is temporarily unavailable.")
        return AIProviderError(f"AWS Bedrock request failed ({code or name}).")
    return AIProviderError(f"AWS Bedrock request failed ({name}).")


def raise_translated_bedrock_error(exc: BaseException) -> NoReturn:
    raise translate_bedrock_error(exc) from exc
