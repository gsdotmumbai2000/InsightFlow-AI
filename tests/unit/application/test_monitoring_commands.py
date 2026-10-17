"""Start/Stop/Renew/GetMonitoringStatus use-case tests (Phase 10)."""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable

import pytest
from tests.fakes.ai import FakeAIProvider
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.dto.models import (
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
    ReprocessAIRequest,
)
from insightflow.application.exceptions.gmail import GmailConnectionError
from insightflow.application.exceptions.monitoring import MonitoringConfigurationError
from insightflow.application.exceptions.pubsub import PubSubConfigurationError
from insightflow.application.process_role import ProcessRole
from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)
from insightflow.domain import AIProfile, SourceType
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)

_NOTIFICATIONS_SETTINGS = NotificationsSettings(enabled=True)

_DISABLED_AI_SETTINGS = AISettings(
    enabled=False,
    automatic_analysis_enabled=True,
    provider="fake",
    region=None,
    model_id="fake-model",
    timeout_seconds=5.0,
    max_retries=0,
    max_input_chars=2_000,
    max_output_tokens=256,
    temperature=0.0,
    queue_max_size=10,
)


def _map_topic(use_cases: ApplicationUseCases, gmail: FakeGmailAdapter) -> str:
    gmail.connect()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    return mapping.topic_id


def _wait_until(predicate: Callable[[], bool], *, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def test_start_monitoring_requires_gmail_connected(
    use_cases: ApplicationUseCases,
) -> None:
    with pytest.raises(GmailConnectionError):
        use_cases.start_monitoring.execute()


def test_start_monitoring_requires_pubsub_authorized(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    _map_topic(use_cases, gmail)
    with pytest.raises(PubSubConfigurationError):
        use_cases.start_monitoring.execute()


def test_start_monitoring_requires_monitored_topics(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    gmail.connect()
    pubsub_authenticator.connect()
    with pytest.raises(MonitoringConfigurationError):
        use_cases.start_monitoring.execute()


def test_start_monitoring_success(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    gmail.message_ids_by_label["Label_TRUMP"] = []

    try:
        status = use_cases.start_monitoring.execute()
        assert status.status == "RUNNING"
        assert status.watch_expiration is not None
        assert len(gmail.watch_calls) == 1
        assert use_cases.monitoring_worker_handle.is_running is True
    finally:
        use_cases.monitoring_worker_handle.stop()


def test_start_monitoring_is_idempotent_when_already_running(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    try:
        use_cases.start_monitoring.execute()
        calls_before = len(gmail.watch_calls)
        use_cases.start_monitoring.execute()
        assert len(gmail.watch_calls) == calls_before
    finally:
        use_cases.monitoring_worker_handle.stop()


def test_stop_monitoring_stops_worker_and_watch(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    status = use_cases.stop_monitoring.execute()

    assert status.status == "STOPPED"
    assert use_cases.monitoring_worker_handle.is_running is False
    assert gmail.stop_watch_calls == 1


def test_renew_gmail_watch_manual_action(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    _map_topic(use_cases, gmail)
    status = use_cases.renew_gmail_watch.execute()
    assert status.watch_expiration is not None
    assert len(gmail.watch_calls) == 1


def test_renew_gmail_watch_requires_gmail_connected(
    use_cases: ApplicationUseCases,
) -> None:
    with pytest.raises(GmailConnectionError):
        use_cases.renew_gmail_watch.execute()


def test_get_monitoring_status_not_configured_when_gmail_disconnected(
    use_cases: ApplicationUseCases,
) -> None:
    status = use_cases.get_monitoring_status.execute()
    assert status.status == "NOT_CONFIGURED"
    assert status.account_email is None


def test_get_monitoring_status_reflects_persisted_state(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    _map_topic(use_cases, gmail)
    use_cases.renew_gmail_watch.execute()
    status = use_cases.get_monitoring_status.execute()
    assert status.account_email == "user@example.com"
    assert status.watched_topic_names == ("TRUMP",)


def test_monitoring_status_dto_never_exposes_credentials(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    _map_topic(use_cases, gmail)
    use_cases.renew_gmail_watch.execute()
    status = use_cases.get_monitoring_status.execute()
    field_names = {f.name for f in dataclasses.fields(status)}
    forbidden = {"token", "credential", "credentials", "secret", "refresh_token"}
    assert not (field_names & forbidden)
    # Also verify no field *value* looks like a token/credential blob.
    for value in dataclasses.astuple(status):
        if isinstance(value, str):
            assert "token" not in value.lower()


def test_gmail_disconnect_stops_active_monitoring(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()
    assert use_cases.monitoring_worker_handle.is_running is True

    use_cases.disconnect_gmail.execute()

    assert use_cases.monitoring_worker_handle.is_running is False


def test_gmail_reconnect_allows_restarting_monitoring(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()
    use_cases.disconnect_gmail.execute()
    assert use_cases.monitoring_worker_handle.is_running is False

    with pytest.raises(GmailConnectionError):
        use_cases.start_monitoring.execute()

    gmail.connect()
    try:
        status = use_cases.start_monitoring.execute()
        assert status.status == "RUNNING"
    finally:
        use_cases.monitoring_worker_handle.stop()


def _build_use_cases_for_same_store(
    store: InMemoryStore,
    gmail: FakeGmailAdapter,
    *,
    role: ProcessRole = ProcessRole.AGENT,
    ai_settings: AISettings | None = None,
) -> ApplicationUseCases:
    """Simulates a fresh application process: a brand-new (empty)
    MonitoringWorkerHandle, wired against the SAME durable store, mirroring
    a real restart where the SQLite file persists but no in-process worker
    exists."""
    pubsub_authenticator = FakePubSubAuthenticator(connected=True)
    pubsub_subscriber = FakePubSubSubscriber()
    pubsub_settings = PubSubSettings(
        project_id="test-project",
        topic="test-gmail-topic",
        subscription="test-gmail-subscription",
        history_batch_size=50,
        history_page_size=100,
        full_sync_max_messages=50,
        watch_renewal_margin_hours=24.0,
        pull_max_messages=10,
        idle_poll_seconds=5.0,
    )
    return build_use_cases(
        store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=pubsub_authenticator,
        pubsub_subscriber_factory=lambda: pubsub_subscriber,
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=pubsub_settings,
        ai_provider=FakeAIProvider(),
        ai_settings=ai_settings or _DISABLED_AI_SETTINGS,
        notification_port=FakeNotificationPort(),
        notifications_settings=_NOTIFICATIONS_SETTINGS,
        startup_registration_port=FakeStartupRegistrationPort(),
        role=role,
    )


def test_running_with_no_live_worker_reconciles_to_paused(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    started = use_cases.start_monitoring.execute()
    assert started.status == "RUNNING"

    # "Restart": a fresh ApplicationUseCases against the same store — no
    # worker exists in this new instance, even though the DB still says
    # RUNNING (mirrors a force-closed/crashed previous process).
    restarted_use_cases = _build_use_cases_for_same_store(store, gmail)
    assert restarted_use_cases.monitoring_worker_handle.is_running is False

    status = restarted_use_cases.get_monitoring_status.execute()

    assert status.status == "PAUSED"

    # The original process's worker is still alive and pulling — stopping
    # it here is just test cleanup, not part of the assertion.
    use_cases.monitoring_worker_handle.stop()


def test_running_with_live_worker_remains_running(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    try:
        status = use_cases.get_monitoring_status.execute()
        assert status.status == "RUNNING"
    finally:
        use_cases.monitoring_worker_handle.stop()


def test_stopped_remains_stopped_when_no_live_worker(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()
    use_cases.stop_monitoring.execute()

    status = use_cases.get_monitoring_status.execute()

    assert status.status == "STOPPED"


def test_reconciliation_persists_so_other_readers_see_it(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    """Dashboard and any future reader must see the corrected status too —
    not just the specific call that happened to trigger reconciliation."""
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    restarted_use_cases = _build_use_cases_for_same_store(store, gmail)
    first_read = restarted_use_cases.get_monitoring_status.execute()
    assert first_read.status == "PAUSED"

    # A second, independent reader (e.g. Dashboard) against the same store
    # must see the already-persisted PAUSED, not a re-derived RUNNING.
    another_restart = _build_use_cases_for_same_store(store, gmail)
    second_read = another_restart.get_monitoring_status.execute()
    assert second_read.status == "PAUSED"

    use_cases.monitoring_worker_handle.stop()


def test_dashboard_summary_reflects_reconciled_status(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    restarted_use_cases = _build_use_cases_for_same_store(store, gmail)
    summary = restarted_use_cases.get_dashboard_summary.execute()

    assert summary.monitoring_status == "PAUSED"

    use_cases.monitoring_worker_handle.stop()


def test_startup_does_not_automatically_start_or_duplicate_workers(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    """A fresh process must never auto-start monitoring, and querying
    status must never itself create a worker."""
    gmail.connect()
    fresh_use_cases = _build_use_cases_for_same_store(store, gmail)

    assert fresh_use_cases.monitoring_worker_handle.is_running is False

    fresh_use_cases.get_monitoring_status.execute()

    assert fresh_use_cases.monitoring_worker_handle.is_running is False


def test_starting_after_reconciliation_creates_exactly_one_worker(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    restarted_use_cases = _build_use_cases_for_same_store(store, gmail)
    restarted_use_cases.get_monitoring_status.execute()  # triggers reconciliation

    try:
        watch_calls_before = len(gmail.watch_calls)
        status = restarted_use_cases.start_monitoring.execute()
        assert status.status == "RUNNING"
        assert restarted_use_cases.monitoring_worker_handle.is_running is True
        # Starting fresh after reconciliation establishes exactly one new
        # watch/worker — not a duplicate on top of the original.
        assert len(gmail.watch_calls) == watch_calls_before + 1
    finally:
        restarted_use_cases.monitoring_worker_handle.stop()
        use_cases.monitoring_worker_handle.stop()


# -- Phase 13: process-role-aware behavior -----------------------------


def test_desktop_role_does_not_reconcile_running_to_paused(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    """Opening the Desktop UI (or its Settings page) while the Agent is
    genuinely running elsewhere must never flip status to PAUSED — the
    Desktop process's own MonitoringWorkerHandle is always empty by design
    (see ProcessRole) and must never be compared against."""
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    started = use_cases.start_monitoring.execute()
    assert started.status == "RUNNING"

    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP
    )
    assert desktop_use_cases.monitoring_worker_handle.is_running is False

    status = desktop_use_cases.get_monitoring_status.execute()
    assert status.status == "RUNNING"

    # Re-reading (e.g. Settings reopened) must remain RUNNING too — not
    # just the first call.
    assert desktop_use_cases.get_monitoring_status.execute().status == "RUNNING"

    use_cases.monitoring_worker_handle.stop()


def test_desktop_role_does_not_start_ai_worker_even_when_enabled(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    enabled = dataclasses.replace(_DISABLED_AI_SETTINGS, enabled=True)
    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP, ai_settings=enabled
    )
    assert desktop_use_cases.ai_worker_handle.is_running is False


def test_agent_role_starts_ai_worker_when_enabled(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    enabled = dataclasses.replace(_DISABLED_AI_SETTINGS, enabled=True)
    agent_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.AGENT, ai_settings=enabled
    )
    try:
        assert agent_use_cases.ai_worker_handle.is_running is True
    finally:
        agent_use_cases.ai_worker_handle.stop(join_timeout_seconds=1.0)


def test_request_start_monitoring_never_touches_worker_handle(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    """The Desktop-role Start Monitoring command only records desired
    state — it is structurally incapable of starting a worker."""
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()

    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP
    )
    status = desktop_use_cases.start_monitoring.execute()

    assert desktop_use_cases.monitoring_worker_handle.is_running is False
    # No watch/worker started, so persisted status remains unchanged by
    # this call — only the desired-state table was written to.
    assert status.status in ("NOT_CONFIGURED", "PAUSED", "STOPPED")
    with store.unit_of_work_factory() as uow:
        account = gmail.get_account()
        assert account is not None
        desired = uow.monitoring_control.get_desired(
            account_id=account.account_id, provider=SourceType.GMAIL
        )
    assert desired.value == "RUNNING"


def test_request_stop_monitoring_never_touches_worker_handle(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()

    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP
    )
    try:
        desktop_use_cases.stop_monitoring.execute()

        # The Agent's own worker is untouched by the Desktop's request —
        # only the reconciler (a separate mechanism) would stop it.
        assert use_cases.monitoring_worker_handle.is_running is True
        with store.unit_of_work_factory() as uow:
            account = gmail.get_account()
            assert account is not None
            desired = uow.monitoring_control.get_desired(
                account_id=account.account_id, provider=SourceType.GMAIL
            )
        assert desired.value == "STOPPED"
    finally:
        use_cases.monitoring_worker_handle.stop()


def test_monitoring_reconciler_starts_worker_to_match_desired_running(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    """End-to-end: Desktop writes desired=RUNNING, the Agent's reconciler
    (constructed for a ProcessRole.AGENT instance) notices and starts the
    worker — without any direct call to StartMonitoringUseCase."""
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()

    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP
    )
    desktop_use_cases.start_monitoring.execute()

    agent_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.AGENT
    )
    try:
        assert agent_use_cases.monitoring_reconciler_handle.is_running is False
        agent_use_cases.monitoring_reconciler_handle.start()
        assert agent_use_cases.monitoring_reconciler_handle.is_running is True
        assert _wait_until(lambda: agent_use_cases.monitoring_worker_handle.is_running)
    finally:
        agent_use_cases.monitoring_reconciler_handle.stop()
        agent_use_cases.monitoring_worker_handle.stop()
        use_cases.monitoring_worker_handle.stop()


def _create_event_for_topic(
    use_cases: ApplicationUseCases,
    store: InMemoryStore,
    *,
    with_profile: bool,
) -> str:
    profile_id: str | None = None
    if with_profile:
        profile = AIProfile.create(
            name="Default", instructions="Summarize.", output_schema_version="v1"
        )
        with store.unit_of_work_factory() as uow:
            uow.profiles.add(profile)
            uow.commit()
        profile_id = profile.id.value
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="AI topic",
            source_type="GENERIC",
            source_id="src",
            source_identifier="ai-topic",
            ai_profile_id=profile_id,
        )
    )
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="src",
            external_id="ai-event",
            topic_id=topic.id,
            title="An event",
            normalized_content="Something happened worth analyzing.",
        )
    )
    return event.id


def test_desktop_reanalyze_is_processed_by_agent_ai_worker(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    """Desktop Analyze only persists AI_PROCESSING; the Agent's AIWorker —
    a different process with its own queue — must pick it up and finish."""
    enabled = dataclasses.replace(_DISABLED_AI_SETTINGS, enabled=True)
    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP, ai_settings=enabled
    )
    event_id = _create_event_for_topic(desktop_use_cases, store, with_profile=True)
    desktop_use_cases.reprocess_ai_analysis.execute(
        ReprocessAIRequest(event_id=event_id)
    )
    assert (
        desktop_use_cases.get_intelligence_event.execute(event_id).status
        == "AI_PROCESSING"
    )

    agent_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.AGENT, ai_settings=enabled
    )
    try:
        assert _wait_until(
            lambda: (
                desktop_use_cases.get_intelligence_event.execute(event_id).status
                == "COMPLETED"
            )
        )
    finally:
        agent_use_cases.ai_worker_handle.stop(join_timeout_seconds=1.0)


def test_agent_ai_worker_fails_stuck_event_it_cannot_analyze(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    """An AI_PROCESSING event whose topic has no AI profile must end FAILED,
    not stay AI_PROCESSING and be re-scanned forever."""
    enabled = dataclasses.replace(_DISABLED_AI_SETTINGS, enabled=True)
    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP, ai_settings=enabled
    )
    event_id = _create_event_for_topic(desktop_use_cases, store, with_profile=False)
    desktop_use_cases.mark_event_processing.execute(event_id)

    agent_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.AGENT, ai_settings=enabled
    )
    try:
        assert _wait_until(
            lambda: (
                desktop_use_cases.get_intelligence_event.execute(event_id).status
                == "FAILED"
            )
        )
    finally:
        agent_use_cases.ai_worker_handle.stop(join_timeout_seconds=1.0)


def test_agent_reconciler_corrects_stale_running_when_desired_stopped(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    store: InMemoryStore,
) -> None:
    """A previous Agent left status RUNNING without stopping, and desired
    state is STOPPED. The Desktop never reconciles and disables Start
    Monitoring while status is RUNNING, so a newly started Agent must
    correct it to PAUSED — otherwise monitoring can never be restarted."""
    _map_topic(use_cases, gmail)
    pubsub_authenticator.connect()
    use_cases.start_monitoring.execute()
    # The previous Agent "dies" without StopMonitoringUseCase: its worker
    # stops but the persisted status stays RUNNING.
    use_cases.monitoring_worker_handle.stop()
    desktop_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.DESKTOP
    )
    desktop_use_cases.stop_monitoring.execute()  # desired=STOPPED only
    assert desktop_use_cases.get_monitoring_status.execute().status == "RUNNING"

    agent_use_cases = _build_use_cases_for_same_store(
        store, gmail, role=ProcessRole.AGENT
    )
    try:
        agent_use_cases.monitoring_reconciler_handle.start()
        assert _wait_until(
            lambda: desktop_use_cases.get_monitoring_status.execute().status == "PAUSED"
        )
        # Correcting the status must not start a worker on its own.
        assert agent_use_cases.monitoring_worker_handle.is_running is False
    finally:
        agent_use_cases.monitoring_reconciler_handle.stop()
        agent_use_cases.monitoring_worker_handle.stop()
