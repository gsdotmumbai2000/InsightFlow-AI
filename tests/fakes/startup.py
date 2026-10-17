"""In-memory fake startup-registration port for tests (Phase 13).

No real ``schtasks.exe`` calls.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeStartupRegistrationPort:
    """Configurable test double for ``StartupRegistrationPort``."""

    registered: bool = False

    def is_registered(self) -> bool:
        return self.registered

    def register(self) -> None:
        self.registered = True

    def unregister(self) -> None:
        self.registered = False
