"""Mutable handle to the currently-running AI worker (Phase 11).

Structurally identical to ``MonitoringWorkerHandle`` (Phase 10): one
process-wide slot so application shutdown can always find and stop the
worker, including during process shutdown, without blocking it.
"""

from __future__ import annotations

from insightflow.application.services.ai_worker import (
    DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    AIWorker,
)


class AIWorkerHandle:
    """One process-wide slot for the active AI worker, if any."""

    def __init__(self) -> None:
        self._worker: AIWorker | None = None

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_running

    def set(self, worker: AIWorker) -> None:
        self._worker = worker

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> None:
        """Request the active worker (if any) to stop.

        Pass ``0`` for a non-blocking stop request — required when calling
        from the Qt GUI thread itself (e.g. on application shutdown).
        """
        if self._worker is not None:
            self._worker.stop(join_timeout_seconds=join_timeout_seconds)
            self._worker = None
