"""Real-time Gmail monitoring use cases (Phase 10)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from insightflow.application._support import unit_of_work_scope, use_case_scope
from insightflow.application.dto.monitoring import (
    MonitoringStatusDto,
    PubSubNotificationDto,
)
from insightflow.application.exceptions import ApplicationError
from insightflow.application.exceptions.gmail import GmailConnectionError
from insightflow.application.exceptions.pubsub import PubSubConfigurationError
from insightflow.application.ports.gmail import GmailAuthenticator
from insightflow.application.ports.pubsub import PubSubAuthenticator, PubSubSubscriber
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.gmail_full_sync import GmailFullSyncService
from insightflow.application.services.gmail_monitoring_worker import (
    GmailMonitoringWorker,
)
from insightflow.application.services.gmail_pubsub_processor import (
    GmailPubSubNotificationProcessor,
)
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)
from insightflow.application.services.monitoring_worker_handle import (
    MonitoringWorkerHandle,
)
from insightflow.domain import MonitoringDesiredStatus, SourceType

logger = logging.getLogger("insightflow.application.monitoring")


class StartMonitoringCommand(Protocol):
    """Whatever ``ApplicationUseCases.start_monitoring`` exposes.

    Two implementations satisfy this, chosen by ``ProcessRole`` (Phase 13):
    ``StartMonitoringUseCase`` (Agent — directly controls the worker) and
    ``RequestStartMonitoringUseCase`` (Desktop — only records desired state).
    Callers (e.g. ``SettingsViewModel``) only ever call ``.execute()``, so
    they need no role-awareness at all.
    """

    def execute(self) -> MonitoringStatusDto: ...


class StopMonitoringCommand(Protocol):
    """See :class:`StartMonitoringCommand`."""

    def execute(self) -> MonitoringStatusDto: ...


class ConnectPubSubUseCase:
    """Run the separate ``pubsub``-scoped OAuth consent for the subscriber."""

    def __init__(self, authenticator: PubSubAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> None:
        with use_case_scope("ConnectPubSub"):
            self._authenticator.connect()


class DisconnectPubSubUseCase:
    def __init__(self, authenticator: PubSubAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> None:
        with use_case_scope("DisconnectPubSub"):
            self._authenticator.disconnect()


class GetPubSubConnectionStatusUseCase:
    """Whether the desktop subscriber currently holds Pub/Sub credentials."""

    def __init__(self, authenticator: PubSubAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> bool:
        with use_case_scope("GetPubSubConnectionStatus"):
            return self._authenticator.is_connected()


class GetMonitoringStatusUseCase:
    """Presentation-safe monitoring status — never includes credentials.

    Reconciles a persisted ``RUNNING``/``STARTING`` status against whether
    this *process* actually has a live worker (``MonitoringWorkerHandle``):
    a status left over from a previous process (closed, crashed, or force-
    terminated without going through ``StopMonitoringUseCase``) is never
    reported as ``RUNNING`` — it is corrected to ``PAUSED`` (and persisted)
    the first time it is observed, so the UI never lies about whether the
    real-time pipeline is actually active. This is the single reconciliation
    point; no other code path re-derives worker liveness independently.

    ``reconcile_worker_liveness`` (Phase 13) must be ``True`` only for the
    instance built in the Background Agent process, which actually owns
    ``MonitoringWorkerHandle``. The Desktop process's handle is *always*
    empty (Desktop never starts a worker — see ``ProcessRole``), so running
    this same reconciliation there would incorrectly flip a genuinely-
    running Agent to ``PAUSED`` the moment Settings is opened. When
    ``False``, this simply returns the persisted status as-is.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        gmail_authenticator: GmailAuthenticator,
        worker_handle: MonitoringWorkerHandle,
        *,
        reconcile_worker_liveness: bool = True,
    ) -> None:
        self._uow_factory = uow_factory
        self._gmail_authenticator = gmail_authenticator
        self._worker_handle = worker_handle
        self._reconcile_worker_liveness = reconcile_worker_liveness

    def execute(self) -> MonitoringStatusDto:
        with (
            use_case_scope("GetMonitoringStatus"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            account = self._gmail_authenticator.get_account()
            watched_topics = tuple(
                topic.name
                for topic in uow.topics.list_enabled()
                if topic.source_configuration.source_type is SourceType.GMAIL
            )
            if account is None:
                return MonitoringStatusDto(
                    status="NOT_CONFIGURED",
                    account_email=None,
                    watched_topic_names=watched_topics,
                    pubsub_project_id=None,
                    pubsub_topic=None,
                    pubsub_subscription=None,
                    watch_expiration=None,
                    last_sync_at=None,
                    last_notification_at=None,
                    last_error=None,
                )
            state = uow.monitoring_states.get_by_account(
                account_id=account.account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return MonitoringStatusDto(
                    status="NOT_CONFIGURED",
                    account_email=account.email,
                    watched_topic_names=watched_topics,
                    pubsub_project_id=None,
                    pubsub_topic=None,
                    pubsub_subscription=None,
                    watch_expiration=None,
                    last_sync_at=None,
                    last_notification_at=None,
                    last_error=None,
                )
            if (
                self._reconcile_worker_liveness
                and state.is_active
                and not self._worker_handle.is_running
            ):
                # Persisted RUNNING/STARTING with no live worker in this
                # process — either the previous process never got to run
                # StopMonitoringUseCase (closed, crashed, force-terminated),
                # or this is a freshly-started process that hasn't clicked
                # Start Monitoring yet. Either way, reporting RUNNING here
                # would be a lie. Reconciled to PAUSED (not STOPPED) to
                # distinguish "was running, needs Start clicked again" from
                # "the user explicitly stopped it" — persisted so every
                # other reader (Dashboard, a future session) sees the
                # corrected value too, not just this call.
                state.mark_paused()
                uow.monitoring_states.update(state)
                uow.commit()
            return MonitoringStatusDto(
                status=state.status.value,
                account_email=account.email,
                watched_topic_names=watched_topics,
                pubsub_project_id=state.pubsub_project_id,
                pubsub_topic=state.pubsub_topic,
                pubsub_subscription=state.pubsub_subscription,
                watch_expiration=state.watch_expiration,
                last_sync_at=state.last_sync_at,
                last_notification_at=state.last_notification_at,
                last_error=state.last_error,
            )


class StartMonitoringUseCase:
    """Establish watch, backfill, and start the background Pub/Sub worker.

    Ordering is deliberate: watch is established *before* the full sync so
    the stored history cursor already covers "now" before backfill begins;
    anything already present is safely caught by the full sync, and
    anything arriving after watch registration triggers a future
    notification. Idempotent dedup (Phase 9) makes the unavoidable overlap
    harmless. See docs/17_Phase10_Gmail_Realtime_Monitoring_Notes.md
    ("watch + initial sync race") for the full rationale.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        gmail_authenticator: GmailAuthenticator,
        pubsub_authenticator: PubSubAuthenticator,
        watch_lifecycle: GmailWatchLifecycleService,
        full_sync: GmailFullSyncService,
        processor: GmailPubSubNotificationProcessor,
        subscriber_factory: Callable[[], PubSubSubscriber],
        parse_notification: Callable[[bytes], PubSubNotificationDto | None],
        worker_handle: MonitoringWorkerHandle,
        status: GetMonitoringStatusUseCase,
        *,
        pull_max_messages: int,
        idle_poll_seconds: float,
        watch_renewal_margin_hours: float,
    ) -> None:
        self._uow_factory = uow_factory
        self._gmail_authenticator = gmail_authenticator
        self._pubsub_authenticator = pubsub_authenticator
        self._watch_lifecycle = watch_lifecycle
        self._full_sync = full_sync
        self._processor = processor
        self._subscriber_factory = subscriber_factory
        self._parse_notification = parse_notification
        self._worker_handle = worker_handle
        self._status = status
        self._pull_max_messages = pull_max_messages
        self._idle_poll_seconds = idle_poll_seconds
        self._watch_renewal_margin_hours = watch_renewal_margin_hours

    def execute(self) -> MonitoringStatusDto:
        with use_case_scope("StartMonitoring"):
            account = self._gmail_authenticator.get_account()
            if account is None:
                raise GmailConnectionError("Connect Gmail before starting monitoring.")
            if not self._pubsub_authenticator.is_connected():
                raise PubSubConfigurationError(
                    "Authorize Pub/Sub access before starting monitoring."
                )
            if self._worker_handle.is_running:
                return self._status.execute()

            account_id = account.account_id
            try:
                self._watch_lifecycle.establish_watch(account_id=account_id)
                self._full_sync.sync_all_monitored_topics()

                worker = GmailMonitoringWorker(
                    account_id=account_id,
                    subscriber=self._subscriber_factory(),
                    processor=self._processor,
                    watch_lifecycle=self._watch_lifecycle,
                    parse_notification=self._parse_notification,
                    pull_max_messages=self._pull_max_messages,
                    idle_poll_seconds=self._idle_poll_seconds,
                    watch_renewal_margin_hours=self._watch_renewal_margin_hours,
                )
                worker.start()
                self._worker_handle.set(worker)
                self._mark_running(account_id)
            except ApplicationError as exc:
                self._mark_error(account_id, str(exc))
                raise
            return self._status.execute()

    def _mark_running(self, account_id: str) -> None:
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.mark_running()
            uow.monitoring_states.update(state)
            # Keep desired state in sync (Phase 13): a direct Start here —
            # not via RequestStartMonitoringUseCase — must still record
            # RUNNING as the desired state, or MonitoringDesiredStateReconciler
            # would see desired=STOPPED (the default) on its very next poll
            # and immediately stop the worker just started.
            uow.monitoring_control.set_desired(
                account_id=account_id,
                provider=SourceType.GMAIL,
                desired=MonitoringDesiredStatus.RUNNING,
            )
            uow.commit()

    def _mark_error(self, account_id: str, message: str) -> None:
        with unit_of_work_scope(self._uow_factory) as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=account_id, provider=SourceType.GMAIL
            )
            if state is None:
                return
            state.mark_error(message)
            uow.monitoring_states.update(state)
            uow.commit()


class StopMonitoringUseCase:
    def __init__(
        self,
        gmail_authenticator: GmailAuthenticator,
        watch_lifecycle: GmailWatchLifecycleService,
        worker_handle: MonitoringWorkerHandle,
        status: GetMonitoringStatusUseCase,
        uow_factory: Callable[[], UnitOfWork],
    ) -> None:
        self._gmail_authenticator = gmail_authenticator
        self._watch_lifecycle = watch_lifecycle
        self._worker_handle = worker_handle
        self._status = status
        self._uow_factory = uow_factory

    def execute(self) -> MonitoringStatusDto:
        with use_case_scope("StopMonitoring"):
            self._worker_handle.stop()
            account = self._gmail_authenticator.get_account()
            if account is not None:
                self._watch_lifecycle.stop_watch(account_id=account.account_id)
                # Keep desired state in sync (Phase 13) — see StartMonitoringUseCase.
                with unit_of_work_scope(self._uow_factory) as uow:
                    uow.monitoring_control.set_desired(
                        account_id=account.account_id,
                        provider=SourceType.GMAIL,
                        desired=MonitoringDesiredStatus.STOPPED,
                    )
                    uow.commit()
            return self._status.execute()


class RequestStartMonitoringUseCase:
    """Desktop-role "Start Monitoring" (Phase 13) — records intent only.

    Never touches ``MonitoringWorkerHandle`` or calls any Gmail/Pub-Sub API:
    it is structurally impossible for the Desktop process to start a worker
    through this class. Validates the same preconditions as
    ``StartMonitoringUseCase`` so the button gives immediate feedback, then
    persists desired=RUNNING for the Background Agent's
    ``MonitoringDesiredStateReconciler`` to act on — typically within one
    poll interval, not synchronously.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        gmail_authenticator: GmailAuthenticator,
        pubsub_authenticator: PubSubAuthenticator,
        status: GetMonitoringStatusUseCase,
    ) -> None:
        self._uow_factory = uow_factory
        self._gmail_authenticator = gmail_authenticator
        self._pubsub_authenticator = pubsub_authenticator
        self._status = status

    def execute(self) -> MonitoringStatusDto:
        with use_case_scope("RequestStartMonitoring"):
            account = self._gmail_authenticator.get_account()
            if account is None:
                raise GmailConnectionError("Connect Gmail before starting monitoring.")
            if not self._pubsub_authenticator.is_connected():
                raise PubSubConfigurationError(
                    "Authorize Pub/Sub access before starting monitoring."
                )
            with unit_of_work_scope(self._uow_factory) as uow:
                uow.monitoring_control.set_desired(
                    account_id=account.account_id,
                    provider=SourceType.GMAIL,
                    desired=MonitoringDesiredStatus.RUNNING,
                )
                uow.commit()
            return self._status.execute()


class RequestStopMonitoringUseCase:
    """Desktop-role "Stop Monitoring" (Phase 13) — records intent only.

    See :class:`RequestStartMonitoringUseCase`.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        gmail_authenticator: GmailAuthenticator,
        status: GetMonitoringStatusUseCase,
    ) -> None:
        self._uow_factory = uow_factory
        self._gmail_authenticator = gmail_authenticator
        self._status = status

    def execute(self) -> MonitoringStatusDto:
        with use_case_scope("RequestStopMonitoring"):
            account = self._gmail_authenticator.get_account()
            if account is not None:
                with unit_of_work_scope(self._uow_factory) as uow:
                    uow.monitoring_control.set_desired(
                        account_id=account.account_id,
                        provider=SourceType.GMAIL,
                        desired=MonitoringDesiredStatus.STOPPED,
                    )
                    uow.commit()
            return self._status.execute()


class RenewGmailWatchUseCase:
    """Manual "Renew Watch" action — also used opportunistically in the worker."""

    def __init__(
        self,
        gmail_authenticator: GmailAuthenticator,
        watch_lifecycle: GmailWatchLifecycleService,
        status: GetMonitoringStatusUseCase,
    ) -> None:
        self._gmail_authenticator = gmail_authenticator
        self._watch_lifecycle = watch_lifecycle
        self._status = status

    def execute(self) -> MonitoringStatusDto:
        with use_case_scope("RenewGmailWatch"):
            account = self._gmail_authenticator.get_account()
            if account is None:
                raise GmailConnectionError("Gmail is not connected.")
            self._watch_lifecycle.establish_watch(account_id=account.account_id)
            return self._status.execute()
