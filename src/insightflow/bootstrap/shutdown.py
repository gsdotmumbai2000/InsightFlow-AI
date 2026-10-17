"""Application shutdown orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from insightflow.infrastructure.logging.setup import get_logger

if TYPE_CHECKING:
    from insightflow.bootstrap.process import Application

logger = get_logger("bootstrap.shutdown")


def shutdown(app: Application) -> None:
    """Release resources held by a running application."""
    logger.info(
        "Shutting down %s v%s",
        app.container.app_name,
        app.container.version,
    )
    # Signal the real-time monitoring worker (if running) to stop, without
    # waiting for it. This runs synchronously on the Qt GUI thread (via
    # MainWindow.closeEvent), so it must never block: a worker that is mid
    # Google API call would otherwise freeze the window for the duration of
    # a blocking join, which is exactly what caused shutdown hangs before
    # this fix. The worker thread is a daemon (see GmailMonitoringWorker),
    # so it can never prevent process exit even if it hasn't finished yet.
    app.container.use_cases.monitoring_worker_handle.stop(join_timeout_seconds=0)
    # Same non-blocking rationale applies to the AI worker (Phase 11): it is
    # also a daemon thread and must never be synchronously joined here.
    app.container.use_cases.ai_worker_handle.stop(join_timeout_seconds=0)
    # And to the monitoring desired-state reconciler (Phase 13, Agent-only —
    # always a harmless no-op in the Desktop process, where it is never set).
    app.container.use_cases.monitoring_reconciler_handle.stop(join_timeout_seconds=0)
