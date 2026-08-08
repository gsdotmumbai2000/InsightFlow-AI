"""Domain-layer exceptions."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain errors."""


class DomainValidationError(DomainError):
    """Raised when a domain value or invariant is invalid."""


class InvalidStateTransitionError(DomainError):
    """Raised when an entity cannot move to the requested state."""
