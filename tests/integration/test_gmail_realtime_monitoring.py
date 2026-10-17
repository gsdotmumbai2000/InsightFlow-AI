"""End-to-end Phase 10 real-time monitoring integration tests.

Exercises the full path: Pub/Sub notification -> Gmail History API ->
EmailMessageDto -> existing Phase 9 ingestion -> IntelligenceEvent,
through a real ``GmailMonitoringWorker`` pull/process/acknowledge loop
against fake Gmail/Pub/Sub ports (no network, no real credentials).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

from insightflow.application.dto.email import EmailAddressDto, EmailMessageDto
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.dto.models import UpdateTopicRequest
from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailHistoryRecordDto,
    PubSubMessageDto,
)
from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)
from insightflow.domain import AIProfile, SourceType
from insightflow.infrastructure.database.unit_of_work import create_unit_of_work
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)
from tests.fakes.ai import FakeAIProvider, make_response
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

ACCOUNT_ID = "user@example.com"

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
_ENABLED_NOTIFICATIONS_SETTINGS = NotificationsSettings(enabled=True)
_DISABLED_NOTIFICATIONS_SETTINGS = NotificationsSettings(enabled=False)
_ENABLED_AI_SETTINGS = AISettings(
    enabled=True,
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


def _email(message_id: str) -> EmailMessageDto:
    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=message_id,
        thread_id=f"thread-{message_id}",
        subject="Trump alert",
        sender=EmailAddressDto(email="alerts@google.com"),
        recipients=(),
        cc=(),
        bcc=(),
        reply_to=(),
        message_id_header=None,
        in_reply_to=None,
        references=(),
        received_at=None,
        date_header=None,
        snippet="snippet",
        text_body="Trump alert body",
        html_body=None,
        label_ids=("Label_TRUMP",),
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def _notification_bytes(history_id: str) -> bytes:
    return json.dumps({"emailAddress": ACCOUNT_ID, "historyId": history_id}).encode()


def _build_use_cases(
    store: InMemoryStore,
    gmail: FakeGmailAdapter,
    *,
    notification_port: FakeNotificationPort | None = None,
    notifications_settings: NotificationsSettings | None = None,
    ai_provider: FakeAIProvider | None = None,
    ai_settings: AISettings | None = None,
) -> tuple[ApplicationUseCases, FakePubSubSubscriber]:
    """Simulates the composition root — same wiring as bootstrap/dependencies.py."""
    subscriber = FakePubSubSubscriber()
    pubsub_authenticator = FakePubSubAuthenticator(connected=True)
    settings = PubSubSettings(
        project_id="test-project",
        topic="gmail-topic",
        subscription="gmail-sub",
        history_batch_size=50,
        history_page_size=100,
        full_sync_max_messages=50,
        watch_renewal_margin_hours=24.0,
        pull_max_messages=10,
        idle_poll_seconds=0.05,
    )
    use_cases = build_use_cases(
        store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=pubsub_authenticator,
        pubsub_subscriber_factory=lambda: subscriber,
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=settings,
        ai_provider=ai_provider or FakeAIProvider(),
        ai_settings=ai_settings or _DISABLED_AI_SETTINGS,
        notification_port=notification_port or FakeNotificationPort(),
        notifications_settings=(
            notifications_settings or _ENABLED_NOTIFICATIONS_SETTINGS
        ),
        startup_registration_port=FakeStartupRegistrationPort(),
    )
    return use_cases, subscriber


def _wait_until(predicate: Callable[[], bool], *, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_end_to_end_notification_creates_intelligence_event() -> None:
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    use_cases, subscriber = _build_use_cases(store, gmail)

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    status = use_cases.start_monitoring.execute()
    assert status.status == "RUNNING"

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )

        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        events = store.events.list_recent()
        assert len(events) == 1
        assert events[0].title == "Trump alert"
        assert events[0].normalized_content == "Trump alert body"
    finally:
        use_cases.stop_monitoring.execute()


def test_duplicate_notification_does_not_duplicate_event() -> None:
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    use_cases, subscriber = _build_use_cases(store, gmail)

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        # No new changes past "1001" — the (duplicate) redelivery re-reads
        # from the already-advanced cursor and finds nothing further.
        gmail.history_pages_by_start_id["1001"] = [
            GmailHistoryPageDto(records=(), next_page_token=None, history_id="1001")
        ]

        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)

        # Duplicate delivery of the identical notification (Pub/Sub at-least-once).
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-2", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-2" in subscriber.acknowledged)

        assert len(store.events.list_recent()) == 1
    finally:
        use_cases.stop_monitoring.execute()


def test_new_realtime_event_triggers_exactly_one_toast_notification() -> None:
    """Phase 12: a genuinely new real-time Gmail event requests one toast."""
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    notification_port = FakeNotificationPort()
    use_cases, subscriber = _build_use_cases(
        store, gmail, notification_port=notification_port
    )

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        assert _wait_until(lambda: len(notification_port.requests) == 1)

        request = notification_port.requests[0]
        assert request.title == "InsightFlow AI — TRUMP"
        assert request.body == "Trump alert"
        assert len(store.notifications.list_recent()) == 1
    finally:
        use_cases.stop_monitoring.execute()


def test_duplicate_pubsub_notification_does_not_duplicate_toast() -> None:
    """Phase 12: a duplicate Pub/Sub redelivery must never produce a second toast."""
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    notification_port = FakeNotificationPort()
    use_cases, subscriber = _build_use_cases(
        store, gmail, notification_port=notification_port
    )

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        gmail.history_pages_by_start_id["1001"] = [
            GmailHistoryPageDto(records=(), next_page_token=None, history_id="1001")
        ]

        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        assert _wait_until(lambda: len(notification_port.requests) == 1)

        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-2", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-2" in subscriber.acknowledged)

        assert len(store.events.list_recent()) == 1
        assert len(notification_port.requests) == 1
    finally:
        use_cases.stop_monitoring.execute()


def test_notifications_disabled_does_not_block_event_creation_or_monitoring() -> None:
    """Phase 12: disabling notifications must not affect Gmail/AI behavior."""
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    notification_port = FakeNotificationPort()
    use_cases, subscriber = _build_use_cases(
        store,
        gmail,
        notification_port=notification_port,
        notifications_settings=_DISABLED_NOTIFICATIONS_SETTINGS,
    )

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    status = use_cases.start_monitoring.execute()
    assert status.status == "RUNNING"

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)

        assert len(store.events.list_recent()) == 1
        assert notification_port.requests == []
        assert use_cases.get_monitoring_status.execute().status == "RUNNING"
    finally:
        use_cases.stop_monitoring.execute()


def test_ai_dispatch_still_occurs_independently_of_notifications() -> None:
    """Phase 12: AI analysis and toast notification are independent dispatchers."""
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    notification_port = FakeNotificationPort()
    ai_provider = FakeAIProvider(response=make_response(summary="AI summary."))
    use_cases, subscriber = _build_use_cases(
        store,
        gmail,
        notification_port=notification_port,
        ai_provider=ai_provider,
        ai_settings=_ENABLED_AI_SETTINGS,
    )

    gmail.connect()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    profile = AIProfile.create(
        name="Default", instructions="Summarize", output_schema_version="v1"
    )
    with store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.commit()
    use_cases.update_topic.execute(
        UpdateTopicRequest(topic_id=mapping.topic_id, ai_profile_id=profile.id.value)
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        assert _wait_until(lambda: len(notification_port.requests) == 1)

        events = store.events.list_recent()
        assert len(events) == 1

        def _analysis_completed() -> bool:
            try:
                return (
                    use_cases.get_ai_analysis.execute(events[0].id.value).status
                    == "COMPLETED"
                )
            except Exception:
                return False

        assert _wait_until(_analysis_completed)
    finally:
        use_cases.stop_monitoring.execute()


def test_recovery_after_restart_processes_pending_work() -> None:
    """Application stopped -> Gmail changes occur -> notification remains
    pending -> application starts -> notification processed -> event created.
    """
    store = InMemoryStore()
    gmail = FakeGmailAdapter()

    # "First run": establish monitoring, then the app stops (worker never
    # started, mirroring an application that never got to process the
    # notification before shutdown).
    use_cases, _first_run_subscriber = _build_use_cases(store, gmail)
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.renew_gmail_watch.execute()

    gmail.messages_by_id["m1"] = _email("m1")
    gmail.history_pages_by_start_id[gmail.watch_history_id] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
            next_page_token=None,
            history_id="1001",
        )
    ]

    # "Restart": fresh ApplicationUseCases wired against the same durable
    # store (a real restart would reopen the same SQLite file).
    use_cases_after_restart, subscriber_after_restart = _build_use_cases(store, gmail)
    status = use_cases_after_restart.start_monitoring.execute()
    assert status.status == "RUNNING"

    try:
        subscriber_after_restart.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber_after_restart.acknowledged)
        assert len(store.events.list_recent()) == 1
    finally:
        use_cases_after_restart.stop_monitoring.execute()


def test_history_gap_triggers_full_sync_and_monitoring_resumes() -> None:
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    use_cases, subscriber = _build_use_cases(store, gmail)

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        # Simulate an expired/unavailable history position.
        gmail.unavailable_history_ids = {gmail.watch_history_id}
        gmail.message_ids_by_label["Label_TRUMP"] = ["m1"]
        gmail.messages_by_id["m1"] = _email("m1")

        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("999999"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)

        events = store.events.list_recent()
        assert len(events) == 1
        with store.unit_of_work_factory() as uow:
            state = uow.monitoring_states.get_by_account(
                account_id=ACCOUNT_ID, provider=SourceType.GMAIL
            )
        assert state is not None
        assert state.status.value == "RUNNING"
    finally:
        use_cases.stop_monitoring.execute()


def test_multiple_sequential_notifications_advance_cursor_correctly() -> None:
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    use_cases, subscriber = _build_use_cases(store, gmail)

    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    use_cases.connect_pubsub.execute()
    use_cases.start_monitoring.execute()

    try:
        start = gmail.watch_history_id
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.messages_by_id["m2"] = _email("m2")
        gmail.history_pages_by_start_id[start] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1010"),),
                next_page_token=None,
                history_id="1010",
            )
        ]
        gmail.history_pages_by_start_id["1010"] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m2", history_id="1020"),),
                next_page_token=None,
                history_id="1020",
            )
        ]

        # One notification can represent multiple mailbox changes; the
        # cursor still advances correctly across sequential notifications.
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1010"))
        )
        assert _wait_until(lambda: "ack-1" in subscriber.acknowledged)
        subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-2", data=_notification_bytes("1020"))
        )
        assert _wait_until(lambda: "ack-2" in subscriber.acknowledged)

        events = store.events.list_recent()
        assert {e.source.external_id for e in events} == {"m1", "m2"}
    finally:
        use_cases.stop_monitoring.execute()


def _build_use_cases_against_sqlite(
    db_path: Path, gmail: FakeGmailAdapter
) -> tuple[ApplicationUseCases, FakePubSubSubscriber]:
    """Same wiring as ``_build_use_cases``, but against a real on-disk
    SQLite database (via the production ``create_unit_of_work`` factory)
    instead of the in-memory fake — used for the acceptance scenario that
    most closely mirrors an actual application restart against a real
    database file."""
    subscriber = FakePubSubSubscriber()
    pubsub_authenticator = FakePubSubAuthenticator(connected=True)
    settings = PubSubSettings(
        project_id="test-project",
        topic="gmail-topic",
        subscription="gmail-sub",
        history_batch_size=50,
        history_page_size=100,
        full_sync_max_messages=50,
        watch_renewal_margin_hours=24.0,
        pull_max_messages=10,
        idle_poll_seconds=0.05,
    )
    use_cases = build_use_cases(
        partial(create_unit_of_work, db_path),
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=pubsub_authenticator,
        pubsub_subscriber_factory=lambda: subscriber,
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=settings,
        ai_provider=FakeAIProvider(),
        ai_settings=_DISABLED_AI_SETTINGS,
        notification_port=FakeNotificationPort(),
        notifications_settings=_ENABLED_NOTIFICATIONS_SETTINGS,
        startup_registration_port=FakeStartupRegistrationPort(),
    )
    return use_cases, subscriber


def test_acceptance_start_close_reopen_no_false_running_start_again_once(
    tmp_path: Path,
) -> None:
    """End-to-end acceptance scenario for the Phase 10 shutdown/stale-state
    correction, against a real SQLite database file (not the in-memory
    fake), matching the exact sequence from the correction's quality-gate
    checklist:

    1. Start Monitoring -> 2. becomes RUNNING -> 3./4. "close application"
    (worker handle dropped, mirroring process exit without Stop Monitoring)
    -> 5. "start application again" (fresh ApplicationUseCases, same DB
    file) -> 6. monitoring does NOT falsely appear RUNNING -> 7. Start
    Monitoring again -> 8./9. worker starts exactly once, no duplicate
    watch/worker.
    """
    db_path = tmp_path / "insightflow.db"
    gmail = FakeGmailAdapter()
    gmail.connect()

    # "First process": start monitoring.
    first_process, _first_subscriber = _build_use_cases_against_sqlite(db_path, gmail)
    first_process.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    first_process.connect_pubsub.execute()
    started = first_process.start_monitoring.execute()
    assert started.status == "RUNNING"
    assert first_process.monitoring_worker_handle.is_running is True

    # "Close application": the process exits without clicking Stop
    # Monitoring — nothing more happens to `first_process` from here; a
    # real process exit would abandon it exactly like this (the shutdown
    # fix guarantees this doesn't hang, but doesn't touch the DB status).

    # "Start application again": brand-new ApplicationUseCases, same file.
    second_process, _second_subscriber = _build_use_cases_against_sqlite(db_path, gmail)
    assert second_process.monitoring_worker_handle.is_running is False

    status_before_start = second_process.get_monitoring_status.execute()
    assert status_before_start.status != "RUNNING"
    assert status_before_start.status == "PAUSED"

    watch_calls_before = len(gmail.watch_calls)
    restarted_status = second_process.start_monitoring.execute()

    assert restarted_status.status == "RUNNING"
    assert second_process.monitoring_worker_handle.is_running is True
    assert len(gmail.watch_calls) == watch_calls_before + 1

    second_process.stop_monitoring.execute()
    first_process.monitoring_worker_handle.stop(join_timeout_seconds=0)
