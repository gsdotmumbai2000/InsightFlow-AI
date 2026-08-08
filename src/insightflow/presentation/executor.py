"""Future-ready UI task execution boundary (sync for Phase 6)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class UiExecutor:
    """Runs presentation-bound work.

    Phase 6 executes synchronously for small/local use cases.
    Later phases may replace this with QThread/QRunnable without
    changing ViewModels that depend on this boundary.
    """

    def run(self, operation: Callable[[], T]) -> T:
        return operation()
