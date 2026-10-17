"""Process-role distinction for the composition root (Phase 13).

``build_container``/``build_use_cases`` are shared by two entry points:
``bootstrap.agent`` (owns ``GmailMonitoringWorker``/``AIWorker``, never
imports Qt) and ``bootstrap.startup`` (the desktop GUI, never owns a
worker). ``ProcessRole`` is the single switch threaded through that
composition root to decide which of the two a given process is.
"""

from __future__ import annotations

from enum import StrEnum


class ProcessRole(StrEnum):
    """Which process a composed :class:`ApplicationUseCases` belongs to."""

    AGENT = "AGENT"
    DESKTOP = "DESKTOP"
