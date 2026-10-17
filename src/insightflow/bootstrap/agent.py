"""Background Agent entry point (Phase 13).

Owns ``GmailMonitoringWorker``, ``AIWorker``, and the monitoring
desired-state reconciler — these keep running whether or not the Desktop
UI is open. Deliberately imports no PySide6/``QApplication`` anywhere in
this module or its dependency chain (see ``bootstrap/__init__.py`` for why
that requires care), so the Agent can run on a machine session with no GUI
event loop at all.

Normally started automatically by a per-user Windows Scheduled Task at
logon (see ``infrastructure.process.windows_startup``, registered via the
Desktop Settings "Start InsightFlow with Windows" toggle). Can also be run
manually for testing: ``insightflow-agent`` (console script) or
``python -m insightflow.bootstrap.agent``.
"""

from __future__ import annotations

import signal
import threading
from types import FrameType

from insightflow.application.process_role import ProcessRole
from insightflow.bootstrap.dependencies import (
    build_container,
    load_runtime_configuration,
)
from insightflow.bootstrap.process import Application
from insightflow.infrastructure.logging.setup import get_logger
from insightflow.infrastructure.process.single_instance import SingleInstanceLock
from insightflow.shared.correlation import correlation_context

logger = get_logger("bootstrap.agent")

AGENT_LOCK_FILENAME = "agent.lock"

# Best-effort only: Task Scheduler typically terminates a non-interactive
# process directly (no signal delivered), so this covers manual runs
# (Ctrl+C / Ctrl+Break) and `taskkill` without `/F`, not every shutdown
# path. Consistent with the rest of the app's shutdown posture (see
# bootstrap/shutdown.py): daemon threads and WAL's crash-safety are the
# real safety net, not a guaranteed clean signal handler.
_SIGNAL_NAMES = ("SIGINT", "SIGTERM", "SIGBREAK")


def main() -> int:
    """CLI entry point for the Background Agent."""
    loaded = load_runtime_configuration()
    loaded.directories.ensure_exists()
    lock_path = loaded.directories.root / AGENT_LOCK_FILENAME
    lock = SingleInstanceLock(lock_path)
    if not lock.acquire():
        logger.error(
            "Another InsightFlow AI Agent instance is already running "
            "(lock held at %s); exiting.",
            lock_path,
        )
        return 1

    try:
        container = build_container(role=ProcessRole.AGENT)
        app = Application(container=container, started=True)
        # Explicit, visible startup step — see MonitoringReconcilerHandle.start().
        container.use_cases.monitoring_reconciler_handle.start()
        with correlation_context():
            logger.info(
                "%s Background Agent started v%s env=%s data_dir=%s",
                container.app_name,
                container.version,
                container.config.application.environment.value,
                container.directories.root,
            )

        stop_event = threading.Event()

        def _handle_signal(signum: int, _frame: FrameType | None) -> None:
            logger.info("Agent received signal %s; shutting down.", signum)
            stop_event.set()

        for name in _SIGNAL_NAMES:
            sig = getattr(signal, name, None)
            if sig is not None:
                signal.signal(sig, _handle_signal)

        try:
            stop_event.wait()
        finally:
            if app.started:
                app.stop()
        return 0
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
