"""AI provider application exceptions (no provider SDK leakage)."""

from __future__ import annotations

from insightflow.application.exceptions.application import ApplicationError


class AIError(ApplicationError):
    """Base AI application error."""


class AIProviderError(AIError):
    """Base error raised by an ``AIProvider`` adapter."""


class AIProviderTimeoutError(AIProviderError):
    """The AI provider did not respond within the configured timeout."""


class AIProviderAuthenticationError(AIProviderError):
    """The AI provider rejected the request's credentials/authorization."""


class AIProviderRateLimitError(AIProviderError):
    """The AI provider throttled the request."""


class AIProviderUnavailableError(AIProviderError):
    """The AI provider is temporarily unavailable, disabled, or unreachable."""


class AIProviderInvalidResponseError(AIProviderError):
    """The AI provider's raw response could not be translated into a DTO."""


class AIResponseValidationError(AIError):
    """A structurally-parsed AI response failed semantic validation."""
