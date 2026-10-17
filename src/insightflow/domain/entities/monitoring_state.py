"""MonitoringState entity — real-time source-monitoring cursor (Phase 10).

Tracks the durable synchronization position for one (account, provider)
pair so mailbox-change processing can resume correctly after a restart,
duplicate notification, or temporary failure. Never holds OAuth tokens,
Pub/Sub credentials, or message content — only coordinates and status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from insightflow.domain.enums import MonitoringStatus, SourceType
from insightflow.domain.value_objects import MonitoringStateId
from insightflow.domain.value_objects._guards import require_aware_utc, utc_now


@dataclass(slots=True)
class MonitoringState:
    """Durable real-time monitoring cursor for one connected account."""

    id: MonitoringStateId
    account_id: str
    provider: SourceType
    pubsub_project_id: str | None
    pubsub_topic: str | None
    pubsub_subscription: str | None
    current_history_id: str | None
    watch_expiration: datetime | None
    status: MonitoringStatus
    last_notification_at: datetime | None
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")
        if self.watch_expiration is not None:
            self.watch_expiration = require_aware_utc(
                self.watch_expiration, "watch_expiration"
            )
        if self.last_notification_at is not None:
            self.last_notification_at = require_aware_utc(
                self.last_notification_at, "last_notification_at"
            )
        if self.last_sync_at is not None:
            self.last_sync_at = require_aware_utc(self.last_sync_at, "last_sync_at")

    @classmethod
    def create(
        cls,
        *,
        account_id: str,
        provider: SourceType = SourceType.GMAIL,
        pubsub_project_id: str | None = None,
        pubsub_topic: str | None = None,
        pubsub_subscription: str | None = None,
        state_id: MonitoringStateId | None = None,
        created_at: datetime | None = None,
    ) -> MonitoringState:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=state_id or MonitoringStateId.generate(),
            account_id=account_id,
            provider=provider,
            pubsub_project_id=pubsub_project_id,
            pubsub_topic=pubsub_topic,
            pubsub_subscription=pubsub_subscription,
            current_history_id=None,
            watch_expiration=None,
            status=MonitoringStatus.NOT_CONFIGURED,
            last_notification_at=None,
            last_sync_at=None,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def mark_starting(self, *, at: datetime | None = None) -> None:
        self.status = MonitoringStatus.STARTING
        self.last_error = None
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_running(self, *, at: datetime | None = None) -> None:
        self.status = MonitoringStatus.RUNNING
        self.last_error = None
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_paused(self, *, at: datetime | None = None) -> None:
        self.status = MonitoringStatus.PAUSED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_stopped(self, *, at: datetime | None = None) -> None:
        self.status = MonitoringStatus.STOPPED
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def mark_error(self, message: str, *, at: datetime | None = None) -> None:
        self.status = MonitoringStatus.ERROR
        self.last_error = message
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def record_error(self, message: str, *, at: datetime | None = None) -> None:
        """Record a transient error without changing the lifecycle status.

        Used for isolated worker-level failures (e.g. one failed Pub/Sub
        pull) that must not flip an otherwise-healthy ``RUNNING`` worker
        into ``ERROR`` and must not stop it — distinct from ``mark_error``,
        which represents an actual lifecycle transition.
        """
        self.last_error = message
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def update_watch(
        self,
        *,
        history_id: str,
        expiration: datetime,
        at: datetime | None = None,
    ) -> None:
        """Record a fresh watch registration (initial or renewed)."""
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.current_history_id = history_id
        self.watch_expiration = require_aware_utc(expiration, "expiration")
        self.updated_at = timestamp

    def advance_history(self, history_id: str, *, at: datetime | None = None) -> None:
        """Advance the synchronization cursor after a successful sync."""
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.current_history_id = history_id
        self.last_sync_at = timestamp
        self.updated_at = timestamp

    def record_notification(self, *, at: datetime | None = None) -> None:
        timestamp = require_aware_utc(at or utc_now(), "at")
        self.last_notification_at = timestamp
        self.updated_at = timestamp

    @property
    def is_active(self) -> bool:
        return self.status in (MonitoringStatus.STARTING, MonitoringStatus.RUNNING)

    def watch_needs_renewal(self, *, now: datetime, margin_hours: float) -> bool:
        """Whether the watch should be renewed given a safety margin."""
        if self.watch_expiration is None:
            return True
        now = require_aware_utc(now, "now")
        remaining = (self.watch_expiration - now).total_seconds() / 3600.0
        return remaining <= margin_hours
