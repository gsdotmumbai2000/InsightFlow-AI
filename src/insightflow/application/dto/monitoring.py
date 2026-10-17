"""Provider-neutral real-time Gmail monitoring DTOs (Phase 10).

Watch/History/Pub-Sub SDK types must never appear here or in any consumer
of this module — infrastructure adapters translate provider payloads into
these DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GmailWatchResultDto:
    """Result of a successful ``users.watch`` (or renewal) call."""

    history_id: str
    expiration: datetime


@dataclass(frozen=True, slots=True)
class GmailHistoryRecordDto:
    """One candidate message referenced by a Gmail history record.

    ``history_id`` is that specific record's position — used to advance
    the synchronization cursor precisely when a sync stops mid-page.
    ``label_ids`` reflects the labels known at the time of the history
    record only — used for cheap pre-filtering. The authoritative label
    set used for topic-relevance decisions comes from re-fetching the
    message (``EmailMessageDto.label_ids``).
    """

    message_id: str
    history_id: str
    label_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GmailHistoryPageDto:
    """One page of ``users.history.list`` results."""

    records: tuple[GmailHistoryRecordDto, ...]
    next_page_token: str | None
    history_id: str | None = None


@dataclass(frozen=True, slots=True)
class PubSubNotificationDto:
    """Parsed Gmail mailbox-change notification payload.

    This is a change *signal*, never the email itself — it identifies the
    mailbox and the history position to synchronize from.
    """

    email_address: str
    history_id: str


@dataclass(frozen=True, slots=True)
class PubSubMessageDto:
    """One pulled Pub/Sub message (already base64-decoded)."""

    ack_id: str
    data: bytes
    message_id: str | None = None
    publish_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class HistorySyncOutcome:
    """Result of one bounded ``GmailHistorySyncService.sync`` call."""

    processed_message_count: int = 0
    created_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    new_history_id: str | None = None
    has_more: bool = False


@dataclass(frozen=True, slots=True)
class MonitoringStatusDto:
    """Presentation-safe monitoring status. Never includes credentials."""

    status: str
    account_email: str | None
    watched_topic_names: tuple[str, ...]
    pubsub_project_id: str | None
    pubsub_topic: str | None
    pubsub_subscription: str | None
    watch_expiration: datetime | None
    last_sync_at: datetime | None
    last_notification_at: datetime | None
    last_error: str | None
