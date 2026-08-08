"""Gmail application exceptions (no Google SDK leakage)."""

from __future__ import annotations

from insightflow.application.exceptions.application import ApplicationError


class GmailError(ApplicationError):
    """Base Gmail application error."""


class GmailAuthenticationError(GmailError):
    """OAuth authentication failed or was cancelled."""


class GmailAuthorizationError(GmailError):
    """User did not grant required permissions."""


class GmailConnectionError(GmailError):
    """Gmail connection is missing or invalid."""


class GmailRateLimitError(GmailError):
    """Gmail API rate limit exceeded."""


class GmailUnavailableError(GmailError):
    """Gmail API temporarily unavailable."""


class GmailConfigurationError(GmailError):
    """Gmail OAuth client configuration is incomplete."""


class GmailReauthenticationRequiredError(GmailError):
    """Stored credentials require interactive re-authentication."""
