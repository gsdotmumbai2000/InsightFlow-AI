"""Application-level monitoring refresh notifications (Phase 10 correction).

The background monitoring worker/processor run on a plain
``threading.Thread`` and must never import PySide6 or any presentation
package (enforced by ``tests/architecture/test_dependency_rules.py``), so
they cannot call into Qt directly to ask the UI to refresh. Instead they
call a plain callback — ``MonitoringEventCallback`` — with no knowledge of
what (if anything) is listening.

``MonitoringEventBroadcaster`` is the late-bindable seam: it is constructed
once at composition-root time, before any Qt object exists, and injected
into the monitoring services. The presentation layer attaches its real
listener (a thread-safe Qt bridge) once the GUI is built, via
``set_listener``. Until then — and in any context with no UI attached at
all, e.g. tests — it is a no-op, so monitoring behavior is identical either
way.
"""

from __future__ import annotations

from collections.abc import Callable

MonitoringEventCallback = Callable[[str], None]


class MonitoringEventBroadcaster:
    """Mutable, late-bindable sink for monitoring refresh events."""

    def __init__(self) -> None:
        self._listener: MonitoringEventCallback | None = None

    def set_listener(self, listener: MonitoringEventCallback | None) -> None:
        self._listener = listener

    def notify(self, reason: str) -> None:
        listener = self._listener
        if listener is not None:
            listener(reason)
