"""Mutable handle to the currently-running Gmail monitoring worker (Phase 10).

Shared by ``StartMonitoringUseCase``/``StopMonitoringUseCase`` and
application shutdown so a background worker started via the UI can always
be found and stopped — including during process shutdown, so no thread
can prevent the application from exiting.
"""

from __future__ import annotations

from insightflow.application.services.gmail_monitoring_worker import (
    DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    GmailMonitoringWorker,
)


class MonitoringWorkerHandle:
    """One process-wide slot for the active monitoring worker, if any."""

    def __init__(self) -> None:
        self._worker: GmailMonitoringWorker | None = None

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_running

    def set(self, worker: GmailMonitoringWorker) -> None:
        self._worker = worker

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> None:
        """Request the active worker (if any) to stop.

        Default: a bounded blocking wait — appropriate for explicit user
        actions like the Settings "Stop Monitoring" button, which run off
        the Qt GUI thread. Pass ``0`` for a non-blocking stop request —
        required when calling from the Qt GUI thread itself (e.g. on
        application shutdown/window close), since the worker is a daemon
        thread and never blocks process exit either way.
        """
        if self._worker is not None:
            self._worker.stop(join_timeout_seconds=join_timeout_seconds)
            self._worker = None
