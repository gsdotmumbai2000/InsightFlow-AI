"""Application directory management tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from insightflow.configuration.directories import default_data_root, resolve_directories
from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.errors import ConfigurationError
from insightflow.configuration.loader import load_config


def test_directory_creation(tmp_path: Path) -> None:
    data_dir = tmp_path / "insightflow-data"
    config = load_config(
        environ=MappingEnvironment({"INSIGHTFLOW_DATA_DIR": str(data_dir)})
    )
    directories = resolve_directories(config)
    directories.ensure_exists()

    assert directories.root == data_dir
    assert directories.database.is_dir()
    assert directories.logs.is_dir()
    assert directories.attachments.is_dir()
    assert directories.temp.is_dir()
    assert directories.exports.is_dir()


def test_configurable_log_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "custom-logs"
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_DATA_DIR": str(data_dir),
                "INSIGHTFLOW_LOG_DIR": str(log_dir),
            }
        )
    )
    directories = resolve_directories(config)
    assert directories.logs == log_dir
    assert directories.root == data_dir


def test_platform_safe_default_windows_style_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("insightflow.configuration.directories.sys.platform", "win32")
    environ = MappingEnvironment({"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"})
    root = default_data_root(environ)
    assert root == Path(r"C:\Users\Example\AppData\Local") / "InsightFlow"


def test_missing_localappdata_requires_explicit_data_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("insightflow.configuration.directories.sys.platform", "win32")
    with pytest.raises(ConfigurationError, match="LOCALAPPDATA"):
        default_data_root(MappingEnvironment({}))
