"""Unit tests for application startup entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from insightflow.bootstrap.startup import Application, create_application, run
from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.models import AppEnvironment
from insightflow.infrastructure.logging.setup import is_logging_configured
from insightflow.infrastructure.secrets.in_memory import InMemorySecretStore


def test_create_application_initializes(
    temp_environ: MappingEnvironment,
) -> None:
    app = create_application(environ=temp_environ)
    try:
        assert isinstance(app, Application)
        assert app.started is True
        assert app.container.app_name == "InsightFlow AI"
        assert app.container.version == "0.1.0"
        assert app.container.config.application.environment is AppEnvironment.TESTING
        assert app.container.directories.root.exists()
        assert app.container.directories.logs.exists()
        assert app.container.database_path.exists()
        assert is_logging_configured() is True
        assert isinstance(app.container.secret_store, InMemorySecretStore)
        assert app.container.diagnostics.logging_initialized is True
        with app.container.unit_of_work_factory() as uow:
            assert uow.topics.list_all() == []
            uow.commit()
    finally:
        app.stop()
        assert app.started is False


def test_run_returns_started_application(temp_environ: MappingEnvironment) -> None:
    app = run(environ=temp_environ)
    try:
        assert app.started is True
    finally:
        app.stop()


def test_main_launches_gui_and_exits_cleanly(tmp_path: Path) -> None:
    """Run the real entrypoint in a subprocess so AUTO_QUIT cannot kill this suite."""
    env = os.environ.copy()
    env.update(
        {
            "INSIGHTFLOW_ENV": "testing",
            "INSIGHTFLOW_DATA_DIR": str(tmp_path / "main-data"),
            "INSIGHTFLOW_LOG_CONSOLE": "false",
            "INSIGHTFLOW_SECRET_STORE": "memory",
            "QT_QPA_PLATFORM": "offscreen",
            "INSIGHTFLOW_UI_AUTO_QUIT": "1",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-m", "insightflow"],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr


def test_create_application_wires_use_cases(
    temp_environ: MappingEnvironment,
) -> None:
    app = create_application(environ=temp_environ)
    try:
        assert app.container.use_cases.list_topics.execute() == []
        summary = app.container.use_cases.get_dashboard_summary.execute()
        assert summary.total_topic_count == 0
    finally:
        app.stop()


def test_graceful_shutdown_still_works(temp_environ: MappingEnvironment) -> None:
    app = create_application(environ=temp_environ)
    app.stop()
    assert app.started is False
