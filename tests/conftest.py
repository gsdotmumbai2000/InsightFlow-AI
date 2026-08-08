"""Shared pytest fixtures for InsightFlow tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from insightflow.configuration.env import MappingEnvironment
from insightflow.infrastructure.logging.setup import reset_logging_state


@pytest.fixture(autouse=True)
def _reset_logging() -> Iterator[None]:
    reset_logging_state()
    yield
    reset_logging_state()


@pytest.fixture
def temp_environ(tmp_path: Path) -> MappingEnvironment:
    """Environment that isolates application data under a temporary directory."""
    return MappingEnvironment(
        {
            "INSIGHTFLOW_ENV": "testing",
            "INSIGHTFLOW_DATA_DIR": str(tmp_path / "data"),
            "INSIGHTFLOW_LOG_LEVEL": "INFO",
            "INSIGHTFLOW_LOG_CONSOLE": "false",
            "INSIGHTFLOW_LOG_FILE": "true",
            "INSIGHTFLOW_SECRET_STORE": "memory",
        }
    )
