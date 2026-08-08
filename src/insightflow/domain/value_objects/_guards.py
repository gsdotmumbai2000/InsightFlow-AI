"""Shared helpers for domain timestamps and strings."""

from __future__ import annotations

from datetime import UTC, datetime

from insightflow.domain.exceptions import DomainValidationError


def require_aware_utc(value: datetime, field_name: str) -> datetime:
    """Require a timezone-aware datetime and normalize to UTC."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise DomainValidationError(
            f"{field_name} must be timezone-aware; naive datetimes are not allowed."
        )
    return value.astimezone(UTC)


def utc_now() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(UTC)


def require_non_empty(value: str, field_name: str) -> str:
    """Require a non-empty, non-whitespace string."""
    if not isinstance(value, str):
        raise DomainValidationError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise DomainValidationError(f"{field_name} must not be empty.")
    return cleaned
