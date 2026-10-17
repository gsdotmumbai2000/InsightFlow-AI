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


class TopicNotGmailConfiguredError(GmailError):
    """Topic has no Gmail label mapping (SourceConfiguration is not GMAIL)."""


class GmailMessageNotFoundError(GmailError):
    """The requested Gmail message ID does not exist or is inaccessible."""


class GmailMessageParsingError(GmailError):
    """A Gmail message could not be normalized (malformed MIME structure)."""


class GmailWatchError(GmailError):
    """Establishing, renewing, or stopping a Gmail watch failed."""


class GmailHistoryUnavailableError(GmailError):
    """The requested startHistoryId is no longer available (Gmail 404).

    Recovery is a full synchronization followed by re-establishing the
    watch to obtain a fresh history baseline.
    """


class GmailHistorySyncError(GmailError):
    """Gmail history synchronization failed for a reason other than 404."""
