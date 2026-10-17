"""No-op startup-registration port for unsupported platforms (Phase 13).

Selected by the composition root when the running OS is not Windows, so
the application never shells out to ``schtasks.exe`` on Linux/macOS.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("insightflow.infrastructure.process")


class UnsupportedStartupRegistrationPort:
    """Gracefully reports that Windows auto-start is unavailable here."""

    def is_registered(self) -> bool:
        return False

    def register(self) -> None:
        logger.debug(
            "Windows Scheduled Task startup registration is not supported on "
            "this platform; ignoring."
        )

    def unregister(self) -> None:
        logger.debug(
            "Windows Scheduled Task startup registration is not supported on "
            "this platform; ignoring."
        )
