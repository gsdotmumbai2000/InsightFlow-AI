"""Map application/domain failures to user-facing UI messages."""

from __future__ import annotations

import logging

from insightflow.application.exceptions import (
    ApplicationError,
    ApplicationValidationError,
    DuplicateEventError,
    DuplicateTopicError,
    InvalidOperationError,
    NotFoundError,
)
from insightflow.application.exceptions.gmail import GmailError

logger = logging.getLogger("insightflow.presentation")


def user_message_for_error(exc: BaseException) -> str:
    """Return a short message suitable for dialogs/status labels."""
    if isinstance(exc, ApplicationValidationError):
        return str(exc) or "The provided information is invalid."
    if isinstance(exc, GmailError):
        return str(exc) or "A Gmail operation failed."
    if isinstance(exc, DuplicateTopicError):
        return "A topic with this source identity already exists."
    if isinstance(exc, DuplicateEventError):
        return "This intelligence event already exists."
    if isinstance(exc, InvalidOperationError):
        return str(exc) or "That action is not allowed in the current state."
    if isinstance(exc, NotFoundError):
        return str(exc) or "The requested item could not be found."
    if isinstance(exc, ApplicationError):
        return str(exc) or "The application could not complete that action."
    logger.exception("Unexpected presentation error", exc_info=exc)
    return "Something went wrong. See diagnostics/logs for details."
