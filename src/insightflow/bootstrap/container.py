"""Composition root container for wiring application dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.ports.secret_store import SecretStore
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.configuration.directories import AppDirectories
from insightflow.configuration.models import AppConfig


@dataclass(slots=True)
class AppContainer:
    """Holds constructed application services for the composition root."""

    app_name: str
    version: str
    config: AppConfig
    directories: AppDirectories
    secret_store: SecretStore
    diagnostics: RuntimeDiagnostics
    database_path: Path
    unit_of_work_factory: Callable[[], UnitOfWork]
    use_cases: ApplicationUseCases
