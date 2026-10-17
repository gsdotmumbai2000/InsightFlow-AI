"""Windows toast notification adapter (Phase 12).

``windows_toasts``/``winrt`` are imported only here, per the architecture
guard tests. The underlying ``WindowsToaster`` is constructed lazily so a
missing/misconfigured Windows notification subsystem never prevents app
startup — the same lazy-construction pattern used by
``BedrockAIProvider`` (Phase 11).

Click-to-activate is intentionally not implemented: reliable
``on_activated`` callbacks require a registered AUMID (e.g. a Start Menu
shortcut), which this desktop application does not set up. Using the
plain ``WindowsToaster`` (rather than ``InteractableWindowsToaster``)
avoids a fragile, unreliable activation mechanism — see
docs/20_Phase12_Windows_Toast_Notifications_Notes.md for the documented
limitation.
"""

from __future__ import annotations

import logging
from typing import Any

from windows_toasts import Toast, WindowsToaster

from insightflow.application.ports.notifications import ToastNotificationRequest

logger = logging.getLogger("insightflow.infrastructure.notifications")

_APPLICATION_TEXT = "InsightFlow AI"


class WindowsToastNotificationPort:
    """``NotificationPort`` implementation backed by native Windows toasts."""

    def __init__(self, application_text: str = _APPLICATION_TEXT) -> None:
        self._application_text = application_text
        self._toaster: Any | None = None

    def _get_toaster(self) -> Any:
        if self._toaster is None:
            self._toaster = WindowsToaster(self._application_text)
        return self._toaster

    def notify(self, request: ToastNotificationRequest) -> None:
        toaster = self._get_toaster()
        toast = Toast([request.title, request.body])
        toaster.show_toast(toast)
        logger.debug(
            "Windows toast displayed event_id=%s",
            request.event_id,
        )
