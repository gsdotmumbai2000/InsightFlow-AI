"""Bootstrap / composition root for InsightFlow AI.

Deliberately does **not** re-export from ``bootstrap.startup`` here: that
module imports ``presentation.app`` (PySide6), and ``bootstrap.agent``
(Phase 13, the headless Background Agent entry point) must not transitively
pull in Qt merely by being a submodule of this package. Import directly
from ``insightflow.bootstrap.startup`` / ``insightflow.bootstrap.agent`` /
``insightflow.bootstrap.dependencies`` etc. instead.
"""

from __future__ import annotations
