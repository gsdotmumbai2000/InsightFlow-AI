"""Application directory resolution and creation."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from insightflow.configuration.env import EnvironmentSource, OsEnvironment
from insightflow.configuration.errors import ConfigurationError
from insightflow.configuration.models import AppConfig, StorageSettings


@dataclass(frozen=True, slots=True)
class AppDirectories:
    """Resolved application filesystem locations."""

    root: Path
    database: Path
    logs: Path
    attachments: Path
    temp: Path
    exports: Path

    def ensure_exists(self) -> None:
        """Create application directories when missing."""
        for path in (
            self.root,
            self.database,
            self.logs,
            self.attachments,
            self.temp,
            self.exports,
        ):
            path.mkdir(parents=True, exist_ok=True)


def default_data_root(environ: EnvironmentSource | None = None) -> Path:
    """Return the platform-appropriate default data root.

    Windows: ``%LOCALAPPDATA%\\InsightFlow``
    macOS: ``~/Library/Application Support/InsightFlow``
    Linux/other: ``~/.local/share/InsightFlow``
    """
    source = environ if environ is not None else OsEnvironment()
    platform_name = sys.platform
    if platform_name == "win32":
        local_app_data = source.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "InsightFlow"
        raise ConfigurationError(
            "LOCALAPPDATA is not set; cannot resolve the default "
            "Windows data directory. "
            "Set INSIGHTFLOW_DATA_DIR to an absolute path."
        )
    if platform_name == "darwin":
        return Path.home() / "Library" / "Application Support" / "InsightFlow"
    return Path.home() / ".local" / "share" / "InsightFlow"


def resolve_directories(
    config: AppConfig,
    *,
    environ: EnvironmentSource | None = None,
) -> AppDirectories:
    """Resolve configured or default application directories."""
    storage: StorageSettings = config.storage
    root = storage.data_dir or default_data_root(environ)
    logs = storage.log_dir or (root / "logs")
    return AppDirectories(
        root=root,
        database=root / "database",
        logs=logs,
        attachments=root / "attachments",
        temp=root / "temp",
        exports=root / "exports",
    )
