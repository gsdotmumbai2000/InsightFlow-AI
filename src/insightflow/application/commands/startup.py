"""Windows auto-start ("Start InsightFlow with Windows") use cases (Phase 13)."""

from __future__ import annotations

from insightflow.application._support import use_case_scope
from insightflow.application.ports.startup import StartupRegistrationPort


class GetStartupRegistrationStatusUseCase:
    def __init__(self, port: StartupRegistrationPort) -> None:
        self._port = port

    def execute(self) -> bool:
        with use_case_scope("GetStartupRegistrationStatus"):
            return self._port.is_registered()


class EnableStartupUseCase:
    """Register the per-user Scheduled Task that starts the Agent at logon."""

    def __init__(self, port: StartupRegistrationPort) -> None:
        self._port = port

    def execute(self) -> bool:
        with use_case_scope("EnableStartup"):
            self._port.register()
            return self._port.is_registered()


class DisableStartupUseCase:
    def __init__(self, port: StartupRegistrationPort) -> None:
        self._port = port

    def execute(self) -> bool:
        with use_case_scope("DisableStartup"):
            self._port.unregister()
            return self._port.is_registered()
