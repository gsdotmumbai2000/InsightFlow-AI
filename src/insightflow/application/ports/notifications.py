"""Provider-neutral notification-delivery port (Phase 12).

No OS-specific notification SDK (WinRT, ``windows_toasts``, etc.) may
appear on this boundary — ``ToastNotificationRequest`` is a plain,
platform-agnostic dataclass carrying only safe, non-secret display text.
Infrastructure adapters (``infrastructure/notifications``) translate this
into whatever a specific delivery mechanism requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ToastNotificationRequest:
    """Everything a notification adapter needs to display one toast."""

    title: str
    body: str
    event_id: str


@runtime_checkable
class NotificationPort(Protocol):
    """Provider-neutral notification delivery boundary."""

    def notify(self, request: ToastNotificationRequest) -> None:
        """Display one notification. Raises on delivery failure."""
