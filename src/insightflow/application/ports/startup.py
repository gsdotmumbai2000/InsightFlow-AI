"""Windows auto-start registration port (Phase 13).

Concrete implementation wraps ``schtasks.exe`` to register/unregister a
per-user Scheduled Task that launches the Background Agent at logon — see
``infrastructure.process.windows_startup``. The application layer never
knows how registration is implemented, only that it can be queried and
toggled.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StartupRegistrationPort(Protocol):
    """Whether the Background Agent is registered to start at Windows logon."""

    def is_registered(self) -> bool: ...
    def register(self) -> None: ...
    def unregister(self) -> None: ...
