"""In-memory fake Pub/Sub ports for unit tests (no network)."""

from __future__ import annotations

from dataclasses import dataclass, field

from insightflow.application.dto.monitoring import PubSubMessageDto


@dataclass
class FakePubSubAuthenticator:
    """Test double for PubSubAuthenticator."""

    connected: bool = False
    connect_calls: int = field(default=0, compare=False)

    def connect(self) -> None:
        self.connect_calls += 1
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected


@dataclass
class FakePubSubSubscriber:
    """In-memory pull queue; supports scripted pull/ack failures for tests."""

    pending: list[PubSubMessageDto] = field(default_factory=list)
    acknowledged: list[str] = field(default_factory=list)
    pull_calls: int = field(default=0, compare=False)
    raise_on_pull: Exception | None = None
    raise_on_ack: Exception | None = None

    def enqueue(self, message: PubSubMessageDto) -> None:
        self.pending.append(message)

    def pull(self, *, max_messages: int) -> list[PubSubMessageDto]:
        self.pull_calls += 1
        if self.raise_on_pull is not None:
            raise self.raise_on_pull
        batch = self.pending[:max_messages]
        self.pending = self.pending[max_messages:]
        return batch

    def acknowledge(self, ack_ids: tuple[str, ...]) -> None:
        if self.raise_on_ack is not None:
            raise self.raise_on_ack
        self.acknowledged.extend(ack_ids)
