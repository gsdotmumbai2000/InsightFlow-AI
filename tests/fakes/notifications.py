"""In-memory fake notification port for tests (no real Windows toasts)."""

from __future__ import annotations

from dataclasses import dataclass, field

from insightflow.application.ports.notifications import ToastNotificationRequest


@dataclass
class FakeNotificationPort:
    """Configurable test double for ``NotificationPort``."""

    error: Exception | None = None
    requests: list[ToastNotificationRequest] = field(default_factory=list)

    def notify(self, request: ToastNotificationRequest) -> None:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
