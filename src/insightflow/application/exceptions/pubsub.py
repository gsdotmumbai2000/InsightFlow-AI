"""Pub/Sub application exceptions (no Google SDK leakage)."""

from __future__ import annotations

from insightflow.application.exceptions.application import ApplicationError


class PubSubError(ApplicationError):
    """Base Pub/Sub application error."""


class PubSubConfigurationError(PubSubError):
    """Pub/Sub project/topic/subscription configuration is incomplete."""


class PubSubAuthenticationError(PubSubError):
    """Pub/Sub OAuth authentication failed, was cancelled, or is missing."""


class PubSubSubscriptionError(PubSubError):
    """A Pub/Sub pull or acknowledge operation failed."""
