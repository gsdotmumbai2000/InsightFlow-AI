"""Minimal presentation refresh hook for future domain-event wiring."""

from __future__ import annotations

from collections.abc import Callable

RefreshListener = Callable[[str], None]


class PresentationRefreshHub:
    """In-process pub/sub for UI refresh signals (not an event bus)."""

    def __init__(self) -> None:
        self._listeners: list[RefreshListener] = []

    def subscribe(self, listener: RefreshListener) -> None:
        self._listeners.append(listener)

    def publish(self, reason: str = "refresh") -> None:
        for listener in list(self._listeners):
            listener(reason)
