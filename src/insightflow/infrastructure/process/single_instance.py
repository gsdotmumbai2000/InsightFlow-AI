"""Windows single-instance protection via stdlib ``msvcrt`` (Phase 13).

Chosen over a named mutex (``pywin32``) specifically to avoid a new
dependency — ``msvcrt`` is stdlib and Windows-only, matching this
codebase's existing platform-conditional-import convention (see
``windows-toasts; sys_platform == 'win32'`` in ``pyproject.toml``). The OS
releases the lock automatically on process exit *or crash*, so there is no
PID-file staleness detection to get wrong: a second Agent launched while
the lock is held simply fails to acquire it and exits immediately.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import IO


class SingleInstanceError(Exception):
    """Raised by ``acquire(strict=True)`` when another instance holds the lock."""


class SingleInstanceLock:
    """Exclusive lock on one file, held for the lifetime of this process."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._file: IO[str] | None = None

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns ``False`` if already held."""
        if sys.platform != "win32":
            raise RuntimeError("SingleInstanceLock is only supported on Windows.")
        import msvcrt

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        file = self._lock_path.open("a+")
        try:
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            file.close()
            return False
        self._file = file
        return True

    def release(self) -> None:
        if self._file is None:
            return
        import msvcrt

        try:
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> SingleInstanceLock:
        if not self.acquire():
            raise SingleInstanceError(
                f"Another InsightFlow AI Agent instance already holds "
                f"{self._lock_path}."
            )
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
