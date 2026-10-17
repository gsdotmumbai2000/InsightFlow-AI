"""Pub/Sub application ports (provider-neutral, Phase 10).

Application code must not import ``googleapiclient``/``google.cloud`` —
only infrastructure implements these Protocols.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from insightflow.application.dto.monitoring import PubSubMessageDto


@runtime_checkable
class PubSubAuthenticator(Protocol):
    """OAuth connect/disconnect/status for the desktop Pub/Sub subscriber.

    Kept separate from :class:`~insightflow.application.ports.gmail.GmailAuthenticator`
    per the project's credential-separation policy: Gmail OAuth requests
    ``gmail.readonly``; this requests the additional ``pubsub`` scope
    through its own consent step and its own stored token, so a user who
    never enables real-time monitoring never grants Pub/Sub access.
    """

    def connect(self) -> None:
        """Run OAuth for the ``pubsub`` scope and persist credentials securely."""
        ...

    def disconnect(self) -> None:
        """Remove stored Pub/Sub credentials."""
        ...

    def is_connected(self) -> bool:
        """Return whether usable Pub/Sub credentials are stored."""
        ...


@runtime_checkable
class PubSubSubscriber(Protocol):
    """Pull/acknowledge messages from a dedicated Pub/Sub subscription.

    Implementations must not acknowledge a message as a side effect of
    ``pull`` — acknowledgement is a separate, explicit call so the caller
    can defer it until processing has safely completed.
    """

    def pull(self, *, max_messages: int) -> list[PubSubMessageDto]:
        """Return up to ``max_messages`` currently available messages."""
        ...

    def acknowledge(self, ack_ids: tuple[str, ...]) -> None:
        """Acknowledge previously pulled messages by ack ID."""
        ...
