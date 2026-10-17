"""Mutable handle to the currently-running monitoring reconciler (Phase 13).

Structurally identical to ``MonitoringWorkerHandle``/``AIWorkerHandle``: one
process-wide slot so application shutdown can always find and stop it,
without blocking. Only ever populated in the Background Agent process — see
``ProcessRole``.
"""

from __future__ import annotations

from insightflow.application.services.monitoring_reconciler import (
    DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    MonitoringDesiredStateReconciler,
)


class MonitoringReconcilerHandle:
    """One process-wide slot for the active reconciler, if any."""

    def __init__(self) -> None:
        self._reconciler: MonitoringDesiredStateReconciler | None = None

    @property
    def is_running(self) -> bool:
        return self._reconciler is not None and self._reconciler.is_running

    def set(self, reconciler: MonitoringDesiredStateReconciler) -> None:
        self._reconciler = reconciler

    def start(self) -> None:
        """Start the reconciler set via :meth:`set`, if any.

        Deliberately **not** called automatically by ``build_use_cases`` —
        every test/caller that builds a ``ProcessRole.AGENT``
        ``ApplicationUseCases`` (the default role) would otherwise get an
        unrequested background thread. Only ``bootstrap.agent`` calls this,
        making "the Agent starts monitoring reconciliation" an explicit,
        visible step in its own startup sequence rather than a hidden
        side effect of dependency injection.
        """
        if self._reconciler is not None:
            self._reconciler.start()

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> None:
        """Request the active reconciler (if any) to stop.

        Pass ``0`` for a non-blocking stop request — required when calling
        from the Qt GUI thread itself (e.g. on application shutdown).
        """
        if self._reconciler is not None:
            self._reconciler.stop(join_timeout_seconds=join_timeout_seconds)
            self._reconciler = None
