"""Per-user Windows Scheduled Task registration for the Background Agent
(Phase 13).

Wraps ``schtasks.exe`` via stdlib ``subprocess`` — no new dependency. The
task triggers ``ONLOGON`` for the current user only (no ``/RU``/``/RP``, so
no stored password, no Administrator rights) at ``/RL LIMITED`` (least
privilege) — this keeps the Agent running in the interactive user session,
which is required for both Windows Toast (WinRT toast APIs need the
interactive session) and Windows Credential Manager (DPAPI is scoped to
the logged-in user). A Windows Service was deliberately rejected in the
Phase 13 architecture review for exactly this reason: Session 0 isolation
breaks Toast notifications.
"""

from __future__ import annotations

import subprocess
import sys

DEFAULT_TASK_NAME = "InsightFlow AI Background Agent"


def default_agent_command() -> str:
    """The command Task Scheduler runs — same interpreter as this process,
    running the Agent entry point as a module (mirrors ``python -m
    insightflow``, the existing desktop entry point convention).
    """
    return f'"{sys.executable}" -m insightflow.bootstrap.agent'


class WindowsScheduledTaskStartup:
    """Registers/queries/removes the per-user logon task via ``schtasks.exe``."""

    def __init__(
        self,
        *,
        task_name: str = DEFAULT_TASK_NAME,
        agent_command: str | None = None,
    ) -> None:
        self._task_name = task_name
        self._agent_command = agent_command or default_agent_command()

    def is_registered(self) -> bool:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", self._task_name],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def register(self) -> None:
        result = subprocess.run(
            [
                "schtasks",
                "/Create",
                "/TN",
                self._task_name,
                "/TR",
                self._agent_command,
                "/SC",
                "ONLOGON",
                "/RL",
                "LIMITED",
                "/F",
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Failed to register InsightFlow AI startup task: "
                f"{result.stderr.decode(errors='replace').strip()}"
            )

    def unregister(self) -> None:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", self._task_name, "/F"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").lower()
            if "cannot find" in stderr or "does not exist" in stderr:
                return  # Already absent — unregistering is idempotent.
            raise RuntimeError(
                "Failed to remove InsightFlow AI startup task: "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
