"""Minimal in-process domain event collection (no event bus)."""

from __future__ import annotations

from dataclasses import dataclass, field

from insightflow.domain.events import (
    AIAnalysisCompleted,
    IntelligenceEventCreated,
    NotificationRequested,
)

DomainEvent = IntelligenceEventCreated | AIAnalysisCompleted | NotificationRequested


@dataclass(slots=True)
class DomainEventCollector:
    """Collects domain events raised during a use-case execution.

    Infrastructure may later drain this collection. Phase 5 does not dispatch.
    """

    _events: list[DomainEvent] = field(default_factory=list)

    def add(self, event: DomainEvent) -> None:
        self._events.append(event)

    def drain(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def peek(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)
