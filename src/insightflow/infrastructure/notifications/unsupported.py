"""No-op notification port for unsupported platforms (Phase 12).

Selected by the composition root when the running OS is not Windows, so
the application never imports ``windows_toasts``/``winrt`` (Windows-only
native bindings) on Linux/macOS and never crashes for lack of them.
"""

from __future__ import annotations

import logging

from insightflow.application.ports.notifications import ToastNotificationRequest

logger = logging.getLogger("insightflow.infrastructure.notifications")


class UnsupportedNotificationPort:
    """Gracefully reports that toast notifications are unavailable here."""

    def notify(self, request: ToastNotificationRequest) -> None:
        logger.debug(
            "Windows toast notifications are not supported on this platform; "
            "skipping event_id=%s",
            request.event_id,
        )
