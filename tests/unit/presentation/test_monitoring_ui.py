"""Settings/Dashboard monitoring UI tests (Phase 10)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from tests.fakes.ai import FakeAIProvider
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.use_cases import build_use_cases
from insightflow.configuration.models import PubSubSettings
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)
from insightflow.presentation.models.context import PresentationContext
from insightflow.presentation.viewmodels.settings_view_model import SettingsViewModel
from insightflow.presentation.views.dashboard_view import DashboardView
from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.windows.main_window import MainWindow


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


def _map_label_to_topic(settings: SettingsView) -> str:
    settings._vm._use_cases.get_gmail_connection_status.execute()
    mapping = settings._vm._use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_2", topic_name="TRUMP")
    )
    return mapping.topic_id


def test_monitoring_status_not_configured_before_gmail_connected(
    qapp: QApplication, main_window: MainWindow
) -> None:
    settings = _settings(main_window)
    settings.refresh()
    qapp.processEvents()

    assert "Status: NOT_CONFIGURED" in settings._monitoring_status.text()
    assert not settings._start_monitoring.isEnabled()
    assert not settings._stop_monitoring.isEnabled()
    assert not settings._renew_watch.isEnabled()
    assert not settings._revoke_pubsub.isEnabled()
    assert settings._authorize_pubsub.isEnabled()


def test_start_monitoring_requires_gmail_and_pubsub(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    settings.refresh()
    qapp.processEvents()

    # Gmail connected but Pub/Sub not authorized: Start remains disabled.
    assert not settings._start_monitoring.isEnabled()


def test_start_stop_monitoring_flow_updates_status_and_buttons(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    _map_label_to_topic(settings)
    pubsub_authenticator.connect()
    settings.refresh()
    qapp.processEvents()

    assert settings._start_monitoring.isEnabled()

    try:
        settings.apply_state(settings._vm.start_monitoring())
        qapp.processEvents()

        assert "Status: RUNNING" in settings._monitoring_status.text()
        assert not settings._start_monitoring.isEnabled()
        assert settings._stop_monitoring.isEnabled()
        assert settings._renew_watch.isEnabled()
        assert not settings._revoke_pubsub.isEnabled()

        settings.apply_state(settings._vm.stop_monitoring())
        qapp.processEvents()

        assert "Status: STOPPED" in settings._monitoring_status.text()
        assert settings._start_monitoring.isEnabled()
        assert not settings._stop_monitoring.isEnabled()
        assert not settings._renew_watch.isEnabled()
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_renew_watch_updates_expiration(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    _map_label_to_topic(settings)
    settings.refresh()
    qapp.processEvents()

    settings.apply_state(settings._vm.renew_watch())
    qapp.processEvents()

    text = settings._monitoring_status.text()
    assert "Watch expiration: —" not in text
    assert "Last error: —" in text


def test_monitoring_status_never_displays_credentials(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    _map_label_to_topic(settings)
    pubsub_authenticator.connect()
    settings.refresh()
    qapp.processEvents()

    try:
        settings.apply_state(settings._vm.start_monitoring())
        qapp.processEvents()

        text = settings._monitoring_status.text().lower()
        for forbidden in ("token", "secret", "credential", "refresh_token"):
            assert forbidden not in text
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def test_dashboard_does_not_show_running_until_monitoring_actually_started(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    _map_label_to_topic(settings)
    pubsub_authenticator.connect()

    dashboard = _dashboard(main_window)
    dashboard.refresh()
    qapp.processEvents()
    assert "Monitoring: Not configured" in dashboard._summary.text()

    try:
        settings.apply_state(settings._vm.start_monitoring())
        qapp.processEvents()

        dashboard.refresh()
        qapp.processEvents()
        assert "Monitoring: RUNNING" in dashboard._summary.text()

        settings.apply_state(settings._vm.stop_monitoring())
        qapp.processEvents()

        dashboard.refresh()
        qapp.processEvents()
        assert "Monitoring: STOPPED" in dashboard._summary.text()
        assert "Monitoring: RUNNING" not in dashboard._summary.text()
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()


def _restarted_settings_view_model(
    memory_store: InMemoryStore,
    gmail: FakeGmailAdapter,
    presentation_context: PresentationContext,
) -> SettingsViewModel:
    """Simulates re-opening Settings in a fresh application process: a
    brand-new ApplicationUseCases (empty MonitoringWorkerHandle) wired
    against the same durable store."""
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
    fresh_use_cases = build_use_cases(
        memory_store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=FakePubSubAuthenticator(connected=True),
        pubsub_subscriber_factory=lambda: FakePubSubSubscriber(),
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=pubsub_settings,
        ai_provider=FakeAIProvider(),
        ai_settings=presentation_context.config.ai,
        notification_port=FakeNotificationPort(),
        notifications_settings=presentation_context.config.notifications,
        startup_registration_port=FakeStartupRegistrationPort(),
    )
    return SettingsViewModel(
        use_cases=fresh_use_cases,
        config=presentation_context.config,
        directories=presentation_context.directories,
        database_path=presentation_context.database_path,
        diagnostics=presentation_context.diagnostics,
    )


def test_settings_shows_paused_after_restart_with_no_live_worker(
    qapp: QApplication,
    main_window: MainWindow,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    memory_store: InMemoryStore,
    presentation_context: PresentationContext,
) -> None:
    settings = _settings(main_window)
    gmail.connect()
    _map_label_to_topic(settings)
    pubsub_authenticator.connect()
    settings.refresh()
    qapp.processEvents()

    try:
        settings.apply_state(settings._vm.start_monitoring())
        qapp.processEvents()
        assert "Status: RUNNING" in settings._monitoring_status.text()

        # A second Settings page in a fresh process, same database.
        restarted_vm = _restarted_settings_view_model(
            memory_store, gmail, presentation_context
        )
        restarted_state = restarted_vm.load()

        assert restarted_state.monitoring_status == "PAUSED"
    finally:
        settings._vm._use_cases.monitoring_worker_handle.stop()
