"""Correlation ID support for asynchronous workflows."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_correlation_id: ContextVar[str | None] = ContextVar(
    "insightflow_correlation_id", default=None
)


def create_correlation_id() -> str:
    """Create a new correlation identifier."""
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    """Return the current correlation ID, if any."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> Token[str | None]:
    """Set the current correlation ID and return a reset token."""
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Restore the previous correlation ID using a context token."""
    _correlation_id.reset(token)


def clear_correlation_id() -> None:
    """Clear the current correlation ID."""
    _correlation_id.set(None)


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[str]:
    """Bind a correlation ID for the duration of a nested operation."""
    value = correlation_id or create_correlation_id()
    token = set_correlation_id(value)
    try:
        yield value
    finally:
        reset_correlation_id(token)
