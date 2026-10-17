"""Shared fixtures for application use-case unit tests."""

from __future__ import annotations

import pytest
from tests.fakes.ai import FakeAIProvider
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.ports.ai import AIProvider
from insightflow.application.ports.notifications import NotificationPort
from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def gmail() -> FakeGmailAdapter:
    return FakeGmailAdapter()


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
    """AI disabled by default; tests that need it override this fixture."""
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
    store: InMemoryStore,
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
        ai_provider=ai_provider,
        ai_settings=ai_settings,
        notification_port=notification_port,
        notifications_settings=notifications_settings,
        startup_registration_port=startup_registration_port,
    )
