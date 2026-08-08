"""Configuration loading and validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.errors import ConfigurationError
from insightflow.configuration.loader import load_config
from insightflow.configuration.models import (
    AppEnvironment,
    LogLevel,
    SecretStoreBackend,
)


def test_default_configuration() -> None:
    config = load_config(environ=MappingEnvironment({}))
    assert config.application.environment is AppEnvironment.DEVELOPMENT
    assert config.logging.level is LogLevel.INFO
    assert config.logging.console_enabled is True
    assert config.logging.file_enabled is True
    assert config.logging.max_bytes == 5_000_000
    assert config.security.secret_store_backend is SecretStoreBackend.MEMORY
    assert config.storage.data_dir is None


def test_environment_variable_override(tmp_path: Path) -> None:
    data_dir = tmp_path / "custom-data"
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_ENV": "testing",
                "INSIGHTFLOW_LOG_LEVEL": "DEBUG",
                "INSIGHTFLOW_LOG_CONSOLE": "false",
                "INSIGHTFLOW_LOG_FILE": "true",
                "INSIGHTFLOW_LOG_MAX_BYTES": "2048",
                "INSIGHTFLOW_LOG_BACKUP_COUNT": "1",
                "INSIGHTFLOW_DATA_DIR": str(data_dir),
                "INSIGHTFLOW_SECRET_STORE": "unavailable",
            }
        )
    )
    assert config.application.environment is AppEnvironment.TESTING
    assert config.logging.level is LogLevel.DEBUG
    assert config.logging.console_enabled is False
    assert config.logging.max_bytes == 2048
    assert config.logging.backup_count == 1
    assert config.storage.data_dir == data_dir
    assert config.security.secret_store_backend is SecretStoreBackend.UNAVAILABLE


def test_dotenv_file_overridden_by_environment(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("INSIGHTFLOW_LOG_LEVEL=DEBUG\n", encoding="utf-8")
    config = load_config(
        environ=MappingEnvironment({"INSIGHTFLOW_LOG_LEVEL": "ERROR"}),
        dotenv_path=dotenv,
    )
    assert config.logging.level is LogLevel.ERROR


def test_discover_dotenv_path_from_project_root(tmp_path: Path) -> None:
    from insightflow.configuration.loader import discover_dotenv_path

    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    dotenv = tmp_path / ".env"
    dotenv.write_text("INSIGHTFLOW_LOG_LEVEL=WARNING\n", encoding="utf-8")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    assert discover_dotenv_path(start=nested) == dotenv


def test_autoload_dotenv_when_environ_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    secrets = tmp_path / "gmail_oauth.json"
    secrets.write_text(
        '{"installed":{"client_id":"x","client_secret":"y"}}', encoding="utf-8"
    )
    (tmp_path / ".env").write_text(
        f"INSIGHTFLOW_GMAIL_CLIENT_SECRETS_FILE={secrets.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    # Clear process env so discovered .env is the only source.
    monkeypatch.delenv("INSIGHTFLOW_GMAIL_CLIENT_SECRETS_FILE", raising=False)
    config = load_config()
    assert config.gmail.client_secrets_file == secrets


def test_invalid_log_level() -> None:
    with pytest.raises(ConfigurationError, match="INSIGHTFLOW_LOG_LEVEL"):
        load_config(environ=MappingEnvironment({"INSIGHTFLOW_LOG_LEVEL": "VERBOSE"}))


def test_invalid_boolean() -> None:
    with pytest.raises(ConfigurationError, match="boolean"):
        load_config(environ=MappingEnvironment({"INSIGHTFLOW_LOG_CONSOLE": "maybe"}))


def test_invalid_numeric_value() -> None:
    with pytest.raises(ConfigurationError, match="integer"):
        load_config(environ=MappingEnvironment({"INSIGHTFLOW_LOG_MAX_BYTES": "big"}))


def test_invalid_numeric_below_minimum() -> None:
    with pytest.raises(ConfigurationError, match=">="):
        load_config(environ=MappingEnvironment({"INSIGHTFLOW_LOG_MAX_BYTES": "0"}))


def test_invalid_environment() -> None:
    with pytest.raises(ConfigurationError, match="INSIGHTFLOW_ENV"):
        load_config(environ=MappingEnvironment({"INSIGHTFLOW_ENV": "staging"}))


def test_relative_data_dir_rejected() -> None:
    with pytest.raises(ConfigurationError, match="absolute"):
        load_config(
            environ=MappingEnvironment({"INSIGHTFLOW_DATA_DIR": "relative/path"})
        )


def test_memory_secret_store_rejected_in_production() -> None:
    with pytest.raises(ConfigurationError, match="not allowed in production"):
        load_config(
            environ=MappingEnvironment(
                {
                    "INSIGHTFLOW_ENV": "production",
                    "INSIGHTFLOW_SECRET_STORE": "memory",
                }
            )
        )


def test_production_defaults_to_windows_secret_store() -> None:
    config = load_config(environ=MappingEnvironment({"INSIGHTFLOW_ENV": "production"}))
    assert config.security.secret_store_backend is SecretStoreBackend.WINDOWS


def test_gmail_settings_loaded(tmp_path: Path) -> None:
    secrets = tmp_path / "client_secret.json"
    secrets.write_text("{}", encoding="utf-8")
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_GMAIL_CLIENT_ID": "cid",
                "INSIGHTFLOW_GMAIL_CLIENT_SECRET": "csecret",
                "INSIGHTFLOW_GMAIL_CLIENT_SECRETS_FILE": str(secrets),
                "INSIGHTFLOW_GMAIL_OAUTH_PORT": "8765",
            }
        )
    )
    assert config.gmail.client_id == "cid"
    assert config.gmail.client_secret == "csecret"
    assert config.gmail.client_secrets_file == secrets
    assert config.gmail.oauth_local_port == 8765
