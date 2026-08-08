"""Configuration provider contract implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from insightflow.configuration.directories import AppDirectories, resolve_directories
from insightflow.configuration.env import EnvironmentSource
from insightflow.configuration.loader import load_config
from insightflow.configuration.models import AppConfig


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """Validated configuration plus resolved directories."""

    config: AppConfig
    directories: AppDirectories


class ConfigurationProvider:
    """Loads, validates, and provides typed configuration."""

    def __init__(
        self,
        *,
        environ: EnvironmentSource | None = None,
        dotenv_path: Path | None = None,
    ) -> None:
        self._environ = environ
        self._dotenv_path = dotenv_path

    def load(self) -> LoadedConfiguration:
        """Load configuration and resolve application directories."""
        config = load_config(environ=self._environ, dotenv_path=self._dotenv_path)
        directories = resolve_directories(config, environ=self._environ)
        return LoadedConfiguration(config=config, directories=directories)
