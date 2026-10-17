"""WindowsToastNotificationPort tests (Phase 12).

The internal ``WindowsToaster`` is replaced with a recording stub before
``notify()`` is ever called — this file must NEVER display a real OS-level
toast. ``Toast(...)`` construction itself is a plain, side-effect-free
dataclass-like object (per ``windows_toasts``); only ``show_toast()``
touches the OS, and that call is intercepted by the stub.
"""

from __future__ import annotations

from typing import Any

from insightflow.application.ports.notifications import ToastNotificationRequest
from insightflow.infrastructure.notifications.unsupported import (
    UnsupportedNotificationPort,
)
from insightflow.infrastructure.notifications.windows_toast import (
    WindowsToastNotificationPort,
)


class _StubToaster:
    def __init__(self) -> None:
        self.toasts: list[Any] = []

    def show_toast(self, toast: Any) -> None:
        self.toasts.append(toast)


def test_notify_uses_toaster_show_toast() -> None:
    port = WindowsToastNotificationPort(application_text="InsightFlow AI")
    stub = _StubToaster()
    port._toaster = stub  # test seam: never construct a real WinRT toaster

    port.notify(
        ToastNotificationRequest(
            title="InsightFlow AI — TRUMP", body="Subject line", event_id="evt-1"
        )
    )

    assert len(stub.toasts) == 1


def test_notify_reuses_the_same_toaster_across_calls() -> None:
    port = WindowsToastNotificationPort()
    stub = _StubToaster()
    port._toaster = stub

    port.notify(ToastNotificationRequest(title="A", body="B", event_id="1"))
    port.notify(ToastNotificationRequest(title="C", body="D", event_id="2"))

    assert len(stub.toasts) == 2
    assert port._toaster is stub  # lazy construction happens at most once


def test_unsupported_notification_port_never_raises() -> None:
    port = UnsupportedNotificationPort()
    port.notify(ToastNotificationRequest(title="A", body="B", event_id="1"))
