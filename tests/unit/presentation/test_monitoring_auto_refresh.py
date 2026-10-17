"""Automatic UI refresh after background monitoring activity (Phase 10 correction).

Verifies that Settings/Dashboard/Intelligence update themselves after the
real background ``GmailMonitoringWorker`` thread processes a Pub/Sub
notification — without the user clicking Refresh — via the existing
``PresentationRefreshHub`` + a thread-safe Qt bridge, never a polling timer.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

import pytest
from PySide6.QtWidgets import QApplication
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber

from insightflow.application.dto.email import EmailAddressDto, EmailMessageDto
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailHistoryRecordDto,
    PubSubMessageDto,
)
from insightflow.configuration.models import PubSubSettings
from insightflow.presentation.monitoring_bridge import MonitoringRefreshBridge
from insightflow.presentation.refresh import PresentationRefreshHub
from insightflow.presentation.views.dashboard_view import DashboardView
from insightflow.presentation.views.intelligence_view import IntelligenceView
from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.windows.main_window import MainWindow

ACCOUNT_ID = "user@example.com"


@pytest.fixture
def pubsub_settings() -> PubSubSettings:
    """Overrides the shared conftest default (5s idle poll) with a fast
    interval, so these tests can observe automatic refresh without a long
    wait — this module-local fixture shadows the conftest one only here."""
    return PubSubSettings(
        project_id="test-project",
        topic="test-gmail-topic",
        subscription="test-gmail-subscription",
        history_batch_size=50,
        history_page_size=100,
        full_sync_max_messages=50,
        watch_renewal_margin_hours=24.0,
        pull_max_messages=10,
        idle_poll_seconds=0.05,
    )


def _settings(main_window: MainWindow) -> SettingsView:
    main_window.navigate_to("settings")
    page = main_window._pages["settings"]
    assert isinstance(page, SettingsView)
    return page


def _dashboard(main_window: MainWindow) -> DashboardView:
    main_window.navigate_to("dashboard")
    page = main_window._pages["dashboard"]
    assert isinstance(page, DashboardView)
    return page


def _intelligence(main_window: MainWindow) -> IntelligenceView:
    main_window.navigate_to("intelligence")
    page = main_window._pages["intelligence"]
    assert isinstance(page, IntelligenceView)
    return page


def _map_label_to_topic(settings: SettingsView) -> str:
    settings._vm._use_cases.get_gmail_connection_status.execute()
    mapping = settings._vm._use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_2", topic_name="TRUMP")
    )
    return mapping.topic_id


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
        label_ids=("Label_2",),
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def _notification_bytes(history_id: str) -> bytes:
    return json.dumps({"emailAddress": ACCOUNT_ID, "historyId": history_id}).encode()


def _pump_until(
    qapp: QApplication, predicate: Callable[[], bool], *, timeout: float = 5.0
) -> bool:
    """Pump the Qt event loop while polling — required for both the
    background worker thread to make progress and the queued cross-thread
    signal / coalescing QTimer to be processed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    qapp.processEvents()
    return predicate()


def _start_monitoring_and_get_subscriber(
    settings: SettingsView,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    gmail.connect()
    _map_label_to_topic(settings)
    pubsub_authenticator.connect()
    status = settings._vm.start_monitoring()
    settings.apply_state(status)
    assert status.monitoring_status == "RUNNING"


def test_settings_last_notification_updates_automatically(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )
    before_text = settings._monitoring_status.text()
    assert "Last notification: —" in before_text

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        pubsub_subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )

        # No manual refresh() / apply_state() call anywhere below — this is
        # the automatic path only.
        updated = _pump_until(
            qapp,
            lambda: "Last notification: —" not in settings._monitoring_status.text(),
        )

        assert updated, settings._monitoring_status.text()
        assert "Last sync: —" not in settings._monitoring_status.text()
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_settings_last_error_updates_automatically(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )
    assert "Last error: —" in settings._monitoring_status.text()

    try:
        pubsub_subscriber.raise_on_pull = RuntimeError("transient network error")

        updated = _pump_until(
            qapp, lambda: "Last error: —" not in settings._monitoring_status.text()
        )

        assert updated, settings._monitoring_status.text()
        assert "Pub/Sub pull failed" in settings._monitoring_status.text()
        assert "RuntimeError" in settings._monitoring_status.text()
        # Sanitized — never the raw exception message.
        assert "transient network error" not in settings._monitoring_status.text()
    finally:
        pubsub_subscriber.raise_on_pull = None
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_dashboard_recent_event_count_updates_automatically(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )

    dashboard = _dashboard(main_window)
    qapp.processEvents()
    assert "Recent events: 0" in dashboard._summary.text()

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        pubsub_subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )

        updated = _pump_until(
            qapp, lambda: "Recent events: 0" not in dashboard._summary.text()
        )

        assert updated, dashboard._summary.text()
        assert "Recent events: 1" in dashboard._summary.text()
        assert "Monitoring: RUNNING" in dashboard._summary.text()
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_intelligence_page_shows_new_event_automatically(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )

    intelligence = _intelligence(main_window)
    qapp.processEvents()
    assert intelligence._table.rowCount() == 0

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        pubsub_subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )

        updated = _pump_until(qapp, lambda: intelligence._table.rowCount() == 1)

        assert updated
        title_item = intelligence._table.item(0, 2)
        assert title_item is not None
        assert title_item.text() == "Trump alert"
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_manual_refresh_button_still_works(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    """Simulates a notification landing while the coalescing window hasn't
    flushed yet, then proves the existing manual Refresh path (SettingsView
    .refresh() -> the same ViewModel.load()) still shows current data
    immediately/independently of the automatic path."""
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )

    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        pubsub_subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )
        assert _pump_until(qapp, lambda: len(pubsub_subscriber.acknowledged) == 1)

        # Manual refresh uses the exact same ViewModel.load() the automatic
        # path uses — no separate/duplicated data-loading logic.
        settings.refresh()
        qapp.processEvents()

        assert "Last notification: —" not in settings._monitoring_status.text()
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_no_spurious_refresh_while_idle(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    """No polling: with nothing happening in the background, no refresh
    event is ever published, even while the Qt event loop keeps running for
    a full second — proving the mechanism is purely reactive to real
    monitoring activity, not a periodic timer."""
    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )

    # Let the coalesced refresh from start_monitoring's own establish_watch()
    # fully flush before establishing the "idle" baseline below — otherwise
    # its deferred (single-shot, ~250ms) timer could fire during the
    # assertion window and look like a spurious idle-time refresh.
    settle_deadline = time.monotonic() + 1.0
    while time.monotonic() < settle_deadline:
        qapp.processEvents()
        time.sleep(0.02)

    published: list[str] = []
    main_window.refresh_hub.subscribe(published.append)

    try:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.02)

        assert published == []
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_monitoring_refresh_bridge_uses_a_single_shot_debounce_not_a_poll(
    qapp: QApplication,
) -> None:
    """The coalescing timer must be single-shot and only ever started in
    response to a real event — never a repeating/periodic timer."""
    hub = PresentationRefreshHub()
    bridge = MonitoringRefreshBridge(hub)

    assert bridge._timer.isSingleShot() is True
    assert bridge._timer.isActive() is False

    bridge.notify("test")
    qapp.processEvents()

    assert bridge._timer.isActive() is True


def test_worker_thread_never_touches_qt_widgets_directly(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
) -> None:
    """GmailMonitoringWorker and the services it calls (application layer)
    have no PySide6 import at all (also enforced by the architecture test
    suite) — this test proves the observable effect: the worker thread can
    successfully drive a UI update end-to-end only through the
    broadcaster/bridge/refresh-hub chain, never by calling widget setters
    itself."""
    import insightflow.application.services.gmail_monitoring_worker as worker_module
    import insightflow.application.services.gmail_pubsub_processor as processor_module

    assert "PySide6" not in dir(worker_module)
    assert "PySide6" not in dir(processor_module)

    settings = _settings(main_window)
    _start_monitoring_and_get_subscriber(
        settings, gmail, pubsub_authenticator, pubsub_subscriber
    )
    try:
        gmail.messages_by_id["m1"] = _email("m1")
        gmail.history_pages_by_start_id[gmail.watch_history_id] = [
            GmailHistoryPageDto(
                records=(GmailHistoryRecordDto(message_id="m1", history_id="1001"),),
                next_page_token=None,
                history_id="1001",
            )
        ]
        pubsub_subscriber.enqueue(
            PubSubMessageDto(ack_id="ack-1", data=_notification_bytes("1001"))
        )

        updated = _pump_until(
            qapp,
            lambda: "Last notification: —" not in settings._monitoring_status.text(),
        )
        assert updated
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()
