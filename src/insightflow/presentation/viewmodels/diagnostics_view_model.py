"""Diagnostics page presentation state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from insightflow.application.use_cases import ApplicationUseCases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.presentation.executor import UiExecutor


@dataclass(frozen=True, slots=True)
class DiagnosticsViewState:
    rows: tuple[tuple[str, str], ...]
    contains_secret_values: bool = False


class DiagnosticsViewModel:
    def __init__(
        self,
        *,
        use_cases: ApplicationUseCases,
        diagnostics: RuntimeDiagnostics,
        database_path: Path,
        app_status: str = "Running",
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._diagnostics = diagnostics
        self._database_path = database_path
        self._app_status = app_status
        self._executor = executor or UiExecutor()

    def load(self) -> DiagnosticsViewState:
        d = self._diagnostics
        gmail_status = "Not connected"
        try:
            status = self._executor.run(
                lambda: self._use_cases.get_gmail_connection_status.execute()
            )
            if status.status == "CONNECTED" and status.account is not None:
                gmail_status = f"Connected ({status.account.email})"
            elif status.status == "REAUTHENTICATION_REQUIRED":
                gmail_status = "Re-authentication required"
            elif status.status == "CONNECTION_FAILED":
                gmail_status = "Connection failed"
            else:
                gmail_status = "Not connected"
        except Exception:
            gmail_status = "Unavailable"

        rows = (
            ("Application", d.app_name),
            ("Version", d.app_version),
            ("Status", self._app_status),
            ("Python", d.python_version),
            ("Operating system", d.operating_system),
            ("Environment", d.environment),
            ("Data directory", d.data_dir),
            ("Log directory", d.log_dir),
            ("Database directory", d.database_dir),
            ("Database file", str(self._database_path)),
            ("Logging level", d.logging_level),
            ("Logging initialized", str(d.logging_initialized)),
            ("Secret store backend", d.secret_store_backend),
            ("Gmail", gmail_status),
            ("AI providers", "Not configured"),
        )
        text = "\n".join(f"{k}: {v}" for k, v in rows).lower()
        secret_markers = ("token", "bearer ", "client_secret", "refresh_token")
        contains_secrets = any(marker in text for marker in secret_markers)
        return DiagnosticsViewState(rows=rows, contains_secret_values=contains_secrets)
