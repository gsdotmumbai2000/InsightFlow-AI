"""Gmail application ports (provider-neutral)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from insightflow.application.dto.email import (
    EmailMessageDto,
    GmailMessageListPageDto,
    ListGmailMessagesRequest,
)
from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
)
from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailWatchResultDto,
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


@runtime_checkable
class GmailMessageProvider(Protocol):
    """Retrieve and normalize Gmail messages for a label (Phase 8).

    Implementations must not expose Google SDK message/service objects;
    callers only see provider-neutral DTOs from ``application.dto.email``.
    """

    def list_message_ids(
        self, request: ListGmailMessagesRequest
    ) -> GmailMessageListPageDto:
        """Return one page of message references for a Gmail label."""
        ...

    def get_message(self, message_id: str) -> EmailMessageDto:
        """Retrieve and normalize a single Gmail message by ID."""
        ...


@runtime_checkable
class GmailWatchProvider(Protocol):
    """Establish/renew/stop Gmail mailbox-change push notifications (Phase 10).

    Backed by ``users.watch`` / ``users.stop``. Never exposes Google SDK
    response objects — only :class:`GmailWatchResultDto`.
    """

    def start_watch(
        self, *, label_ids: tuple[str, ...], pubsub_topic: str
    ) -> GmailWatchResultDto:
        """Register (or re-register) a watch for the given labels.

        Idempotent: calling this again (e.g. after a label change, or to
        renew before expiration) simply resets the expiration and returns
        a fresh ``history_id`` baseline.
        """
        ...

    def stop_watch(self) -> None:
        """Stop all push notifications for the connected mailbox."""
        ...


@runtime_checkable
class GmailHistoryProvider(Protocol):
    """Read mailbox change history since a known position (Phase 10).

    Backed by ``users.history.list``. Raises
    :class:`~insightflow.application.exceptions.gmail.GmailHistoryUnavailableError`
    when ``start_history_id`` is no longer available (Gmail 404) — callers
    must fall back to a full synchronization.
    """

    def list_history(
        self,
        *,
        start_history_id: str,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> GmailHistoryPageDto:
        """Return one page of mailbox changes after ``start_history_id``."""
        ...
