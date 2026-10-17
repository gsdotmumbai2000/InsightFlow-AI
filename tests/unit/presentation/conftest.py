"""Shared fixtures for presentation/UI tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from tests.fakes.ai import FakeAIProvider
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import GmailLabelDto
from insightflow.application.ports.ai import AIProvider
from insightflow.application.ports.notifications import NotificationPort
from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.bootstrap.dependencies import build_container
from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)
from insightflow.presentation.app import build_main_window, create_qapplication
from insightflow.presentation.models.context import PresentationContext
from insightflow.presentation.windows.main_window import MainWindow

_QAPP: QApplication | None = None


@pytest.fixture
def qapp() -> QApplication:
    """Process-wide QApplication for offscreen UI tests (never destroyed)."""
    global _QAPP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if _QAPP is None:
        _QAPP = create_qapplication(["insightflow-test"])
    return _QAPP


@pytest.fixture
def memory_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def gmail() -> FakeGmailAdapter:
    return FakeGmailAdapter(
        labels=[
            GmailLabelDto(label_id="Label_1", name="INBOX", label_type="system"),
            GmailLabelDto(label_id="Label_2", name="TRUMP", label_type="user"),
        ]
    )


@pytest.fixture
def pubsub_authenticator() -> FakePubSubAuthenticator:
    return FakePubSubAuthenticator()


@pytest.fixture
def pubsub_subscriber() -> FakePubSubSubscriber:
    return FakePubSubSubscriber()


@pytest.fixture
def pubsub_settings() -> PubSubSettings:
    return PubSubSettings(
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


@pytest.fixture
def ai_provider() -> FakeAIProvider:
    return FakeAIProvider()


@pytest.fixture
def ai_settings() -> AISettings:
    return AISettings(
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


@pytest.fixture
def notification_port() -> FakeNotificationPort:
    return FakeNotificationPort()


@pytest.fixture
def notifications_settings() -> NotificationsSettings:
    return NotificationsSettings(enabled=True)


@pytest.fixture
def startup_registration_port() -> FakeStartupRegistrationPort:
    return FakeStartupRegistrationPort()


@pytest.fixture
def use_cases(
    memory_store: InMemoryStore,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
    pubsub_settings: PubSubSettings,
    ai_provider: AIProvider,
    ai_settings: AISettings,
    notification_port: NotificationPort,
    notifications_settings: NotificationsSettings,
    startup_registration_port: FakeStartupRegistrationPort,
) -> ApplicationUseCases:
    return build_use_cases(
        memory_store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=pubsub_authenticator,
        pubsub_subscriber_factory=lambda: pubsub_subscriber,
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=pubsub_settings,
        ai_provider=ai_provider,
        ai_settings=ai_settings,
        notification_port=notification_port,
        notifications_settings=notifications_settings,
        startup_registration_port=startup_registration_port,
    )


@pytest.fixture
def presentation_context(
    temp_environ: MappingEnvironment,
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    pubsub_authenticator: FakePubSubAuthenticator,
    pubsub_subscriber: FakePubSubSubscriber,
    ai_provider: AIProvider,
    notification_port: NotificationPort,
) -> PresentationContext:
    container = build_container(
        environ=temp_environ,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=pubsub_authenticator,
        pubsub_subscriber_factory=lambda: pubsub_subscriber,
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        ai_provider=ai_provider,
        notification_port=notification_port,
    )
    return PresentationContext(
        app_name=container.app_name,
        version=container.version,
        config=container.config,
        directories=container.directories,
        diagnostics=container.diagnostics,
        database_path=container.database_path,
        use_cases=use_cases,
    )


@pytest.fixture
def main_window(
    qapp: QApplication, presentation_context: PresentationContext
) -> Iterator[MainWindow]:
    assert qapp is not None
    window = build_main_window(presentation_context)
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
    window.show()
    qapp.processEvents()
    yield window
    window.hide()
    window.close()
    qapp.processEvents()
