"""Shared running-application handle (Phase 13 extraction).

Lives outside ``bootstrap.startup`` specifically so ``bootstrap.agent`` can
reuse it without transitively importing ``presentation.app`` (PySide6) — the
Background Agent must never import Qt.
"""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.bootstrap.container import AppContainer
from insightflow.bootstrap.shutdown import shutdown


@dataclass(slots=True)
class Application:
    """Running application handle produced by startup."""

    container: AppContainer
    started: bool = False

    def stop(self) -> None:
        """Shut down the application cleanly."""
        shutdown(self)
        self.started = False
