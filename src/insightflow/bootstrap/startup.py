"""Application startup orchestration."""

from __future__ import annotations

import sys
from pathlib import Path

from insightflow.application.process_role import ProcessRole
from insightflow.bootstrap.dependencies import build_container
from insightflow.bootstrap.presentation import presentation_context_from_container
from insightflow.bootstrap.process import Application as Application
from insightflow.configuration.env import EnvironmentSource
from insightflow.infrastructure.logging.setup import get_logger
from insightflow.presentation.app import run_gui
from insightflow.shared.correlation import correlation_context

logger = get_logger("bootstrap.startup")


def create_application(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> Application:
    """Initialize configuration, logging, directories, and dependencies.

    Always built as ``ProcessRole.DESKTOP`` (Phase 13): this is the GUI
    entry point (``python -m insightflow`` / the ``insightflow`` console
    script) and must never own ``GmailMonitoringWorker``/``AIWorker`` — see
    ``bootstrap.agent`` for the process that does.
    """
    container = build_container(
        environ=environ, dotenv_path=dotenv_path, role=ProcessRole.DESKTOP
    )
    app = Application(container=container, started=True)
    with correlation_context():
        logger.info(
            "Started %s v%s env=%s data_dir=%s",
            container.app_name,
            container.version,
            container.config.application.environment.value,
            container.directories.root,
        )
    return app


def run(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> Application:
    """Create and return a started application instance."""
    return create_application(environ=environ, dotenv_path=dotenv_path)


def _start_background_agent(app: Application) -> None:
    """Best effort: the Desktop must still open if the Agent can't start."""
    if sys.platform != "win32":
        return
    from insightflow.infrastructure.process.agent_launcher import (
        launch_background_agent,
    )

    try:
        launch_background_agent(log_dir=app.container.directories.logs)
    except Exception:
        logger.warning("Could not start the Background Agent.", exc_info=True)
    else:
        logger.info("Background Agent launch requested.")


def main() -> int:
    """CLI entry point used by ``python -m insightflow`` and console script."""
    app = run()
    _start_background_agent(app)
    try:
        with correlation_context():
            logger.info(
                "%s launching desktop UI (Phase 6).",
                app.container.app_name,
            )
            logger.info(
                "Diagnostics: python=%s os=%s log_level=%s secret_store=%s db=%s",
                app.container.diagnostics.python_version,
                app.container.diagnostics.operating_system,
                app.container.diagnostics.logging_level,
                app.container.diagnostics.secret_store_backend,
                app.container.database_path,
            )
        return run_gui(
            presentation_context_from_container(app.container),
            on_close=app.stop,
        )
    finally:
        if app.started:
            app.stop()
