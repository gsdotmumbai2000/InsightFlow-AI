"""Runtime diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from insightflow.configuration.diagnostics import collect_diagnostics
from insightflow.configuration.directories import resolve_directories
from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.loader import load_config


def test_diagnostics_contains_version_python_and_os(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_ENV": "testing",
                "INSIGHTFLOW_DATA_DIR": str(tmp_path / "data"),
            }
        )
    )
    directories = resolve_directories(config)
    diagnostics = collect_diagnostics(
        config=config,
        directories=directories,
        logging_initialized=True,
    )
    assert diagnostics.app_version == "0.1.0"
    assert diagnostics.python_version
    assert diagnostics.operating_system
    assert diagnostics.environment == "testing"
    assert diagnostics.logging_initialized is True
    assert str(directories.root) == diagnostics.data_dir


def test_diagnostics_do_not_leak_secrets(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_DATA_DIR": str(tmp_path / "data"),
                "INSIGHTFLOW_SECRET_STORE": "memory",
            }
        )
    )
    directories = resolve_directories(config)
    diagnostics = collect_diagnostics(
        config=config,
        directories=directories,
        logging_initialized=False,
    )
    public = diagnostics.as_public_dict()
    serialized = str(public).lower()
    assert "token" not in serialized
    assert "password" not in serialized
    assert "api_key" not in serialized
    assert public["secret_store_backend"] == "memory"
