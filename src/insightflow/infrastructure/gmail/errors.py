"""Translate Google / transport errors into application Gmail errors."""

from __future__ import annotations

import logging
from typing import NoReturn

from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailAuthorizationError,
    GmailConnectionError,
    GmailRateLimitError,
    GmailReauthenticationRequiredError,
    GmailUnavailableError,
)

logger = logging.getLogger("insightflow.infrastructure.gmail")


def raise_translated_google_error(exc: BaseException) -> NoReturn:
    """Map a Google/network exception to an application Gmail error and raise."""
    name = type(exc).__name__
    module = type(exc).__module__
    logger.warning(
        "Gmail infrastructure error category=%s module=%s",
        name,
        module,
    )

    message = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "resp", None)
    status_code = getattr(status, "status", None) if status is not None else None
    if status_code is None and hasattr(exc, "status_code"):
        status_code = exc.status_code

    if status_code == 401 or "invalid_grant" in message or "unauthorized" in message:
        raise GmailReauthenticationRequiredError(
            "Gmail credentials are no longer valid. Please connect Gmail again."
        ) from exc
    if status_code == 403 or "access_denied" in message or "insufficient" in message:
        raise GmailAuthorizationError(
            "Gmail access was denied or required permissions are missing."
        ) from exc
    if status_code == 429 or "rate limit" in message or "quota" in message:
        raise GmailRateLimitError(
            "Gmail API rate limit exceeded. Try again later."
        ) from exc
    if status_code in {500, 502, 503, 504} or "unavailable" in message:
        raise GmailUnavailableError(
            "Gmail is temporarily unavailable. Try again later."
        ) from exc
    if "refresh" in message and ("fail" in message or "error" in message):
        raise GmailReauthenticationRequiredError(
            "Gmail token refresh failed. Please connect Gmail again."
        ) from exc
    if "auth" in message or "oauth" in message or "credential" in message:
        raise GmailAuthenticationError("Gmail authentication failed.") from exc
    raise GmailConnectionError("Gmail connection failed.") from exc
