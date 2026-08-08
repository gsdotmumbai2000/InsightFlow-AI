"""Application exceptions package."""

from __future__ import annotations

from insightflow.application.exceptions.application import (
    AIAnalysisNotFoundError,
    AIProfileNotFoundError,
    ApplicationError,
    ApplicationValidationError,
    AttachmentNotFoundError,
    DuplicateEventError,
    DuplicateTopicError,
    EventNotFoundError,
    InvalidOperationError,
    NotFoundError,
    NotificationNotFoundError,
    StoryNotFoundError,
    TopicNotFoundError,
)
from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailAuthorizationError,
    GmailConfigurationError,
    GmailConnectionError,
    GmailError,
    GmailRateLimitError,
    GmailReauthenticationRequiredError,
    GmailUnavailableError,
)
from insightflow.application.exceptions.persistence import (
    DatabaseUnavailableError,
    DataMappingError,
    DuplicateEntityError,
    PersistenceError,
    TransactionError,
)

__all__ = [
    "AIAnalysisNotFoundError",
    "AIProfileNotFoundError",
    "ApplicationError",
    "ApplicationValidationError",
    "AttachmentNotFoundError",
    "DataMappingError",
    "DatabaseUnavailableError",
    "DuplicateEntityError",
    "DuplicateEventError",
    "DuplicateTopicError",
    "EventNotFoundError",
    "GmailAuthenticationError",
    "GmailAuthorizationError",
    "GmailConfigurationError",
    "GmailConnectionError",
    "GmailError",
    "GmailRateLimitError",
    "GmailReauthenticationRequiredError",
    "GmailUnavailableError",
    "InvalidOperationError",
    "NotFoundError",
    "NotificationNotFoundError",
    "PersistenceError",
    "StoryNotFoundError",
    "TopicNotFoundError",
    "TransactionError",
]
