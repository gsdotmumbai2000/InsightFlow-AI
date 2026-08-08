"""Presentation-facing runtime context (no bootstrap dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from insightflow.application.use_cases import ApplicationUseCases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.configuration.directories import AppDirectories
from insightflow.configuration.models import AppConfig


@dataclass(slots=True)
class PresentationContext:
    """Values the UI needs from the composition root."""

    app_name: str
    version: str
    config: AppConfig
    directories: AppDirectories
    diagnostics: RuntimeDiagnostics
    database_path: Path
    use_cases: ApplicationUseCases
