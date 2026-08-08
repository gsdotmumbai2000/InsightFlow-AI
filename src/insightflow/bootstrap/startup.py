"""Application startup orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from insightflow.bootstrap.container import AppContainer
from insightflow.bootstrap.dependencies import build_container
from insightflow.bootstrap.presentation import presentation_context_from_container
from insightflow.bootstrap.shutdown import shutdown
from insightflow.configuration.env import EnvironmentSource
from insightflow.infrastructure.logging.setup import get_logger
from insightflow.presentation.app import run_gui
from insightflow.shared.correlation import correlation_context

logger = get_logger("bootstrap.startup")


@dataclass(slots=True)
class Application:
    """Running application handle produced by startup."""

    container: AppContainer
    started: bool = False

    def stop(self) -> None:
        """Shut down the application cleanly."""
        shutdown(self)
        self.started = False


def create_application(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> Application:
    """Initialize configuration, logging, directories, and dependencies."""
    container = build_container(environ=environ, dotenv_path=dotenv_path)
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


def main() -> int:
    """CLI entry point used by ``python -m insightflow`` and console script."""
    app = run()
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
