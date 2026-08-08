"""Gmail application ports (provider-neutral)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
)


@runtime_checkable
class GmailAuthenticator(Protocol):
    """OAuth connect / disconnect / status for a Gmail account."""

    def connect(self) -> GmailAccountDto:
        """Run OAuth, persist credentials securely, return account info."""
        ...

    def disconnect(self) -> None:
        """Remove stored credentials and clear connection state."""
        ...

    def get_connection_status(self) -> GmailConnectionStatusDto:
        """Return safe connection status (no tokens)."""
        ...

    def get_account(self) -> GmailAccountDto | None:
        """Return connected account profile, or None if not connected."""
        ...


@runtime_checkable
class GmailLabelProvider(Protocol):
    """Discover Gmail labels for the connected account."""

    def list_labels(self) -> list[GmailLabelDto]:
        """List labels for the currently connected Gmail account."""
        ...
