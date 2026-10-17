"""Gmail watch lifecycle: establish, renew, and stop push notifications.

``establish_watch`` is used for both initial setup and 404-recovery
re-baselining — calling ``users.watch`` again is documented as idempotent
(it simply resets expiration and returns a fresh historyId), so one method
safely serves both cases.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from insightflow.application._support import unit_of_work_scope
from insightflow.application.exceptions.gmail import GmailConnectionError
from insightflow.application.exceptions.monitoring import MonitoringConfigurationError
from insightflow.application.ports.gmail import GmailWatchProvider
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.monitored_labels import monitored_label_ids
from insightflow.application.services.monitoring_events import (
    MonitoringEventCallback,
)
from insightflow.domain import MonitoringState, SourceType

logger = logging.getLogger("insightflow.application.monitoring")


def _noop_event(reason: str) -> None:
    del reason


class GmailWatchLifecycleService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        watch: GmailWatchProvider,
        *,
        pubsub_project_id: str | None,
        pubsub_topic_name: str | None,
        pubsub_subscription: str | None,
        on_event: MonitoringEventCallback = _noop_event,
    ) -> None:
        self._uow_factory = uow_factory
        self._watch = watch
        self._pubsub_project_id = pubsub_project_id
        self._pubsub_topic_name = pubsub_topic_name
        self._pubsub_subscription = pubsub_subscription
        self._on_event = on_event

    @property
    def pubsub_topic_resource(self) -> str | None:
        """Fully qualified topic name Gmail requires: projects/*/topics/*."""
        if not self._pubsub_project_id or not self._pubsub_topic_name:
            return None
        return f"projects/{self._pubsub_project_id}/topics/{self._pubsub_topic_name}"

    def establish_watch(self, *, account_id: str) -> MonitoringState:
        """Start, renew, or re-baseline the Gmail watch for monitored labels."""
        topic_resource = self.pubsub_topic_resource
        if topic_resource is None:
            raise MonitoringConfigurationError(
                "Gmail Pub/Sub project/topic are not configured."
            )
        with unit_of_work_scope(self._uow_factory) as uow:
            label_ids = monitored_label_ids(uow)
        if not label_ids:
            raise MonitoringConfigurationError(
                "No enabled Gmail-mapped Topics to monitor."
            )

        result = self._watch.start_watch(
            label_ids=label_ids, pubsub_topic=topic_resource
        )

        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                state = MonitoringState.create(
                    account_id=account_id,
                    pubsub_project_id=self._pubsub_project_id,
                    pubsub_topic=self._pubsub_topic_name,
                    pubsub_subscription=self._pubsub_subscription,
                )
                state.update_watch(
                    history_id=result.history_id, expiration=result.expiration
                )
                uow.monitoring_states.add(state)
            else:
                state.pubsub_project_id = self._pubsub_project_id
                state.pubsub_topic = self._pubsub_topic_name
                state.pubsub_subscription = self._pubsub_subscription
                state.update_watch(
                    history_id=result.history_id, expiration=result.expiration
                )
                uow.monitoring_states.update(state)
            uow.commit()
            logger.info(
                "Gmail watch established account_id=%s labels=%s expiration=%s",
                account_id,
                len(label_ids),
                result.expiration.isoformat(),
            )
            self._on_event("watch_updated")
            return state

    def stop_watch(self, *, account_id: str) -> MonitoringState | None:
        with contextlib.suppress(GmailConnectionError):
            self._watch.stop_watch()
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return None
            state.mark_stopped()
            uow.monitoring_states.update(state)
            uow.commit()
            logger.info("Gmail watch stopped account_id=%s", account_id)
            self._on_event("watch_stopped")
            return state

    def renew_if_needed(
        self, *, account_id: str, margin_hours: float
    ) -> MonitoringState | None:
        """Renew the watch when within ``margin_hours`` of expiration.

        A cheap no-op read when renewal is not yet due — safe to call
        frequently from a background loop (this is not Gmail polling: it
        only performs a local state read unless renewal truly fires).
        """
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
        if state is None or not state.is_active:
            return state
        if not state.watch_needs_renewal(
            now=datetime.now(UTC), margin_hours=margin_hours
        ):
            return state
        logger.info("Renewing Gmail watch account_id=%s", account_id)
        return self.establish_watch(account_id=account_id)
