"""Background monitoring desired-state reconciler (Phase 13).

Runs on a plain ``threading.Thread`` daemon, never Qt — mirrors
``GmailMonitoringWorker``/``AIWorker``. Agent-only (see ``ProcessRole``):
this is the mechanism that makes the Desktop UI's Start/Stop Monitoring
buttons — which, in the split-process architecture, can only *record*
desired state (see ``RequestStartMonitoringUseCase``/
``RequestStopMonitoringUseCase``) — actually take effect, and what makes
"Windows Login -> monitoring becomes available" true after a reboot: on
every poll it compares persisted desired state against whether *this*
process's ``MonitoringWorkerHandle`` is actually running, and calls the
Agent's own ``StartMonitoringUseCase``/``StopMonitoringUseCase`` to close
the gap. No IPC, no network port — the database is the coordination point.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope
from insightflow.application.commands.monitoring import (
    StartMonitoringCommand,
    StopMonitoringCommand,
)
from insightflow.application.ports.gmail import GmailAuthenticator
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.monitoring_worker_handle import (
    MonitoringWorkerHandle,
)
from insightflow.domain import MonitoringDesiredStatus, SourceType

logger = logging.getLogger("insightflow.application.monitoring")

DEFAULT_POLL_SECONDS = 5.0
DEFAULT_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class MonitoringDesiredStateReconciler:
    """Owns one background thread reconciling actual state to desired state."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        gmail_authenticator: GmailAuthenticator,
        worker_handle: MonitoringWorkerHandle,
        start: StartMonitoringCommand,
        stop: StopMonitoringCommand,
        refresh_status: Callable[[], object] | None = None,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        self._uow_factory = uow_factory
        self._gmail_authenticator = gmail_authenticator
        self._worker_handle = worker_handle
        self._start = start
        self._stop = stop
        self._refresh_status = refresh_status
        self._poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="monitoring-reconciler", daemon=True
        )
        self._thread.start()
        logger.info("Monitoring desired-state reconciler started")

    def stop(
        self,
        *,
        join_timeout_seconds: float | None = DEFAULT_STOP_JOIN_TIMEOUT_SECONDS,
    ) -> bool:
        """Request the reconciler to stop.

        Pass ``0``/``None`` for a non-blocking stop (e.g. on shutdown) —
        the thread is a daemon and can never block process exit either way.
        """
        self._stop_event.set()
        thread = self._thread
        if thread is not None and join_timeout_seconds:
            thread.join(timeout=join_timeout_seconds)
        still_alive = thread is not None and thread.is_alive()
        if not still_alive:
            self._thread = None
        logger.info(
            "Monitoring desired-state reconciler stop requested stopped=%s",
            not still_alive,
        )
        return not still_alive

    def _run(self) -> None:
        self._correct_stale_status()
        while not self._stop_event.is_set():
            self._reconcile_once()
            self._stop_event.wait(self._poll_seconds)

    def _correct_stale_status(self) -> None:
        """Correct a persisted RUNNING/STARTING left behind by a previous Agent.

        The Desktop never reconciles worker liveness (see
        ``GetMonitoringStatusUseCase``) and disables Start Monitoring while
        the status reads RUNNING. If the previous Agent exited without
        stopping (closed console, crash, logoff) and desired state is
        STOPPED, nothing would otherwise ever correct that status, leaving
        Start Monitoring permanently disabled. One Agent-side status read at
        startup flips it to PAUSED so the Desktop can request a start again.
        """
        if self._refresh_status is None:
            return
        try:
            self._refresh_status()
        except Exception as exc:
            logger.warning(
                "Monitoring stale-status correction failed error=%s",
                type(exc).__name__,
            )

    def _reconcile_once(self) -> None:
        try:
            account = self._gmail_authenticator.get_account()
            if account is None:
                return
            with unit_of_work_scope(self._uow_factory) as uow:
                desired = uow.monitoring_control.get_desired(
                    account_id=account.account_id, provider=SourceType.GMAIL
                )
            running = self._worker_handle.is_running
            if desired is MonitoringDesiredStatus.RUNNING and not running:
                self._start.execute()
            elif desired is MonitoringDesiredStatus.STOPPED and running:
                self._stop.execute()
        except Exception as exc:
            logger.warning(
                "Monitoring desired-state reconciliation failed error=%s",
                type(exc).__name__,
            )
