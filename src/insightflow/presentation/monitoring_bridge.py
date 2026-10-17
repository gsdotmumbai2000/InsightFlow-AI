"""Thread-safe bridge from background monitoring events to the Qt GUI thread.

``GmailMonitoringWorker`` (a plain ``threading.Thread``, never Qt) calls
``MonitoringEventBroadcaster.notify`` from its own background thread after
processing a Pub/Sub notification, a watch renewal, or a worker-level error.
This bridge is the presentation-layer listener attached to that broadcaster
(see ``application/services/monitoring_events.py``): it is the only place
a background monitoring thread's activity crosses into Qt.

Thread safety: ``notify()`` only emits a Qt signal, which is safe to call
from any thread. Qt's default connection type becomes a queued connection
whenever the emitting thread differs from the receiving QObject's thread,
so ``_on_event_received`` always runs on the GUI thread that owns this
bridge — no widget is ever touched from the worker thread.

Coalescing: rapid-fire events (e.g. a burst of Pub/Sub messages) are
collapsed into a single ``PresentationRefreshHub.publish`` call via a
short single-shot timer that only ever runs in response to a real event —
this is debouncing, not a periodic UI-refresh poll.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from insightflow.presentation.refresh import PresentationRefreshHub

DEFAULT_COALESCE_MS = 250


class MonitoringRefreshBridge(QObject):
    """Qt-side listener for ``MonitoringEventBroadcaster``."""

    _event_received = Signal(str)

    def __init__(
        self,
        refresh_hub: PresentationRefreshHub,
        *,
        coalesce_ms: int = DEFAULT_COALESCE_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._refresh_hub = refresh_hub
        self._pending_reason: str | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(coalesce_ms)
        self._timer.timeout.connect(self._flush)
        self._event_received.connect(self._on_event_received)

    def notify(self, reason: str) -> None:
        """Safe to call from any thread, including the monitoring worker."""
        self._event_received.emit(reason)

    def _on_event_received(self, reason: str) -> None:
        # Runs on the GUI thread — Qt queues cross-thread signal delivery.
        self._pending_reason = reason
        if not self._timer.isActive():
            self._timer.start()

    def _flush(self) -> None:
        reason = self._pending_reason or "monitoring"
        self._pending_reason = None
        self._refresh_hub.publish(reason)
