"""Runtime diagnostics that never expose secrets."""

from __future__ import annotations

import platform
import sys
from dataclasses import asdict, dataclass
from typing import Any

from insightflow.configuration.directories import AppDirectories
from insightflow.configuration.models import AppConfig


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    """Safe diagnostic snapshot for support and startup verification."""

    app_name: str
    app_version: str
    python_version: str
    operating_system: str
    environment: str
    data_dir: str
    log_dir: str
    database_dir: str
    logging_level: str
    logging_console_enabled: bool
    logging_file_enabled: bool
    logging_initialized: bool
    secret_store_backend: str

    def as_public_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict with no secret material."""
        return asdict(self)


def collect_diagnostics(
    *,
    config: AppConfig,
    directories: AppDirectories,
    logging_initialized: bool,
) -> RuntimeDiagnostics:
    """Collect non-sensitive runtime diagnostics."""
    return RuntimeDiagnostics(
        app_name=config.application.name,
        app_version=config.application.version,
        python_version=sys.version.split()[0],
        operating_system=(
            f"{platform.system()} {platform.release()} ({platform.machine()})"
        ),
        environment=config.application.environment.value,
        data_dir=str(directories.root),
        log_dir=str(directories.logs),
        database_dir=str(directories.database),
        logging_level=config.logging.level.value,
        logging_console_enabled=config.logging.console_enabled,
        logging_file_enabled=config.logging.file_enabled,
        logging_initialized=logging_initialized,
        secret_store_backend=config.security.secret_store_backend.value,
    )
