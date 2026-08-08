"""Shared helpers for application use cases."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from insightflow.application.exceptions import (
    ApplicationValidationError,
    DuplicateEntityError,
    DuplicateEventError,
    DuplicateTopicError,
    InvalidOperationError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import DomainValidationError, InvalidStateTransitionError
from insightflow.shared.correlation import correlation_context

logger = logging.getLogger("insightflow.application")


@contextmanager
def use_case_scope(operation: str) -> Iterator[None]:
    """Establish correlation context for an application operation."""
    with correlation_context():
        logger.debug("Starting use case %s", operation)
        try:
            yield
        finally:
            logger.debug("Finished use case %s", operation)


@contextmanager
def unit_of_work_scope(
    uow_factory: Callable[[], UnitOfWork],
) -> Iterator[UnitOfWork]:
    """Open a unit of work for a use case."""
    with uow_factory() as uow:
        yield uow


def translate_domain_errors(exc: Exception) -> Exception:
    """Map domain/persistence errors to application errors."""
    if isinstance(exc, DomainValidationError):
        return ApplicationValidationError(str(exc))
    if isinstance(exc, InvalidStateTransitionError):
        return InvalidOperationError(str(exc))
    if isinstance(exc, DuplicateEntityError):
        message = str(exc).lower()
        if "topic" in message:
            return DuplicateTopicError(str(exc))
        if "event" in message or "intelligence_event" in message:
            return DuplicateEventError(str(exc))
        return DuplicateEntityError(str(exc))
    return exc


def run_mutating[T](operation: Callable[[], T]) -> T:
    """Execute a mutating use-case body with error translation."""
    try:
        return operation()
    except ValueError as exc:
        raise ApplicationValidationError(str(exc)) from exc
    except (
        DomainValidationError,
        InvalidStateTransitionError,
        DuplicateEntityError,
    ) as exc:
        raise translate_domain_errors(exc) from exc
