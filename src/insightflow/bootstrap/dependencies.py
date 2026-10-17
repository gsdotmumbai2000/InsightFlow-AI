"""Bootstrap dependency factories."""

from __future__ import annotations

import platform
from collections.abc import Callable
from pathlib import Path
from typing import cast

from insightflow.application.dto.monitoring import PubSubNotificationDto
from insightflow.application.ports.ai import AIProvider
from insightflow.application.ports.gmail import (
    GmailAuthenticator,
    GmailHistoryProvider,
    GmailLabelProvider,
    GmailMessageProvider,
    GmailWatchProvider,
)
from insightflow.application.ports.notifications import NotificationPort
from insightflow.application.ports.pubsub import PubSubAuthenticator, PubSubSubscriber
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.ports.secret_store import SecretStore
from insightflow.application.ports.startup import StartupRegistrationPort
from insightflow.application.process_role import ProcessRole
from insightflow.application.use_cases import build_use_cases
from insightflow.bootstrap.container import AppContainer
from insightflow.configuration.diagnostics import collect_diagnostics
from insightflow.configuration.env import EnvironmentSource
from insightflow.configuration.models import AppConfig, SecretStoreBackend
from insightflow.configuration.provider import (
    ConfigurationProvider,
    LoadedConfiguration,
)
from insightflow.infrastructure.ai.bedrock_adapter import BedrockAIProvider
from insightflow.infrastructure.database.connection import connect
from insightflow.infrastructure.database.migrations import initialize_database
from insightflow.infrastructure.database.unit_of_work import SQLiteUnitOfWork
from insightflow.infrastructure.gmail.adapter import GoogleGmailAdapter
from insightflow.infrastructure.gmail.monitoring_adapter import (
    GoogleGmailMonitoringAdapter,
)
from insightflow.infrastructure.logging.setup import (
    configure_logging,
    get_logger,
    is_logging_configured,
)
from insightflow.infrastructure.notifications.unsupported import (
    UnsupportedNotificationPort,
)
from insightflow.infrastructure.pubsub.adapter import GooglePubSubAdapter
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)
from insightflow.infrastructure.pubsub.oauth import GooglePubSubAuthenticator
from insightflow.infrastructure.secrets.in_memory import InMemorySecretStore
from insightflow.infrastructure.secrets.unavailable import UnavailableSecretStore
from insightflow.infrastructure.secrets.windows_keyring import WindowsKeyringSecretStore

logger = get_logger("bootstrap.dependencies")


def build_secret_store(config: AppConfig) -> SecretStore:
    """Create the configured secret-store implementation."""
    backend = config.security.secret_store_backend
    if backend is SecretStoreBackend.MEMORY:
        return InMemorySecretStore()
    if backend is SecretStoreBackend.WINDOWS:
        return WindowsKeyringSecretStore()
    return UnavailableSecretStore()


def build_gmail_adapter(
    config: AppConfig, secret_store: SecretStore
) -> GoogleGmailAdapter:
    """Assemble the Google Gmail adapter (authenticator + label provider)."""
    return GoogleGmailAdapter(
        settings=config.gmail,
        secret_store=secret_store,
        oauth_port=config.gmail.oauth_local_port,
    )


def build_pubsub_authenticator(
    config: AppConfig, secret_store: SecretStore
) -> GooglePubSubAuthenticator:
    """Assemble the separate Pub/Sub OAuth authenticator (Phase 10)."""
    return GooglePubSubAuthenticator(
        settings=config.gmail,
        secret_store=secret_store,
        oauth_port=config.gmail.oauth_local_port,
    )


def build_pubsub_subscriber_factory(
    config: AppConfig, pubsub_authenticator: GooglePubSubAuthenticator
) -> Callable[[], PubSubSubscriber]:
    """Return a factory that builds a fresh subscriber against the configured
    subscription, resolving current (possibly refreshed) credentials each call.
    """
    project_id = config.pubsub.project_id
    subscription = config.pubsub.subscription

    def factory() -> PubSubSubscriber:
        credentials = pubsub_authenticator.credentials()
        subscription_path = f"projects/{project_id}/subscriptions/{subscription}"
        return cast(
            PubSubSubscriber,
            GooglePubSubAdapter(
                credentials=credentials, subscription_path=subscription_path
            ),
        )

    return factory


def build_ai_provider(config: AppConfig) -> AIProvider:
    """Assemble the configured AI provider adapter (Bedrock only, Phase 11).

    AWS credentials are resolved by boto3's default credential chain; the
    client itself is constructed lazily on first use inside the adapter so
    a missing/misconfigured AWS environment never prevents app startup.
    """
    return BedrockAIProvider(
        model_id=config.ai.model_id,
        region=config.ai.region,
        timeout_seconds=config.ai.timeout_seconds,
        max_retries=config.ai.max_retries,
    )


def build_notification_port() -> NotificationPort:
    """Assemble the configured notification adapter (Windows toast, Phase 12).

    ``windows_toasts``/``winrt`` are imported lazily, only when running on
    Windows, so a non-Windows platform never attempts to import a native
    module that (per ``pyproject.toml``) is not even installed there.
    """
    if platform.system() == "Windows":
        from insightflow.infrastructure.notifications.windows_toast import (
            WindowsToastNotificationPort,
        )

        return WindowsToastNotificationPort()
    return UnsupportedNotificationPort()


def build_startup_registration_port() -> StartupRegistrationPort:
    """Assemble the Windows auto-start (Scheduled Task) adapter (Phase 13)."""
    if platform.system() == "Windows":
        from insightflow.infrastructure.process.windows_startup import (
            WindowsScheduledTaskStartup,
        )

        return WindowsScheduledTaskStartup()
    from insightflow.infrastructure.process.unsupported_startup import (
        UnsupportedStartupRegistrationPort,
    )

    return UnsupportedStartupRegistrationPort()


def load_runtime_configuration(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> LoadedConfiguration:
    """Load and validate configuration through the configuration provider."""
    provider = ConfigurationProvider(environ=environ, dotenv_path=dotenv_path)
    return provider.load()


def resolve_database_path(directories_database: Path) -> Path:
    """Return the SQLite file path under the configured database directory."""
    return directories_database / "insightflow.db"


def initialize_app_database(database_path: Path) -> None:
    """Create/migrate the application database at startup."""
    connection = connect(database_path)
    try:
        applied = initialize_database(connection)
        if applied:
            logger.info("Applied database migrations: %s", applied)
        else:
            logger.info("Database schema is up to date at %s", database_path)
    finally:
        connection.close()


def build_unit_of_work_factory(database_path: Path) -> Callable[[], UnitOfWork]:
    """Return a factory that creates a new SQLite unit of work."""

    def factory() -> UnitOfWork:
        return cast(UnitOfWork, SQLiteUnitOfWork(database_path))

    return factory


def build_container(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
    gmail_authenticator: GmailAuthenticator | None = None,
    gmail_labels: GmailLabelProvider | None = None,
    gmail_messages: GmailMessageProvider | None = None,
    gmail_watch: GmailWatchProvider | None = None,
    gmail_history: GmailHistoryProvider | None = None,
    pubsub_authenticator: PubSubAuthenticator | None = None,
    pubsub_subscriber_factory: Callable[[], PubSubSubscriber] | None = None,
    parse_pubsub_notification: (
        Callable[[bytes], PubSubNotificationDto | None] | None
    ) = None,
    ai_provider: AIProvider | None = None,
    notification_port: NotificationPort | None = None,
    startup_registration_port: StartupRegistrationPort | None = None,
    role: ProcessRole = ProcessRole.AGENT,
) -> AppContainer:
    """Create the application dependency container.

    Optional overrides are for tests (fake ports). Production assembles
    concrete Google adapters here. ``role`` (Phase 13) is forwarded to
    ``build_use_cases`` — see its docstring; ``bootstrap.startup`` (Desktop)
    passes ``ProcessRole.DESKTOP`` explicitly, ``bootstrap.agent`` relies on
    the ``AGENT`` default.
    """
    loaded = load_runtime_configuration(environ=environ, dotenv_path=dotenv_path)
    loaded.directories.ensure_exists()
    configure_logging(loaded.config.logging, loaded.directories.logs)

    database_path = resolve_database_path(loaded.directories.database)
    initialize_app_database(database_path)

    secret_store = build_secret_store(loaded.config)
    diagnostics = collect_diagnostics(
        config=loaded.config,
        directories=loaded.directories,
        logging_initialized=is_logging_configured(),
    )

    uow_factory = build_unit_of_work_factory(database_path)
    gmail = build_gmail_adapter(loaded.config, secret_store)
    gmail_monitoring = GoogleGmailMonitoringAdapter(gmail)
    pubsub_auth = build_pubsub_authenticator(loaded.config, secret_store)

    authenticator: GmailAuthenticator = gmail_authenticator or gmail
    labels: GmailLabelProvider = gmail_labels or gmail
    messages: GmailMessageProvider = gmail_messages or gmail
    watch: GmailWatchProvider = gmail_watch or gmail_monitoring
    history: GmailHistoryProvider = gmail_history or gmail_monitoring
    pubsub_authn: PubSubAuthenticator = pubsub_authenticator or pubsub_auth
    subscriber_factory: Callable[[], PubSubSubscriber] = (
        pubsub_subscriber_factory
        or build_pubsub_subscriber_factory(loaded.config, pubsub_auth)
    )
    notification_parser: Callable[[bytes], PubSubNotificationDto | None] = (
        parse_pubsub_notification or parse_gmail_pubsub_notification
    )
    ai: AIProvider = ai_provider or build_ai_provider(loaded.config)
    notifications: NotificationPort = notification_port or build_notification_port()
    startup_registration: StartupRegistrationPort = (
        startup_registration_port or build_startup_registration_port()
    )

    return AppContainer(
        app_name=loaded.config.application.name,
        version=loaded.config.application.version,
        config=loaded.config,
        directories=loaded.directories,
        secret_store=secret_store,
        diagnostics=diagnostics,
        database_path=database_path,
        unit_of_work_factory=uow_factory,
        use_cases=build_use_cases(
            uow_factory,
            gmail_authenticator=authenticator,
            gmail_labels=labels,
            gmail_messages=messages,
            gmail_watch=watch,
            gmail_history=history,
            pubsub_authenticator=pubsub_authn,
            pubsub_subscriber_factory=subscriber_factory,
            parse_pubsub_notification=notification_parser,
            pubsub_settings=loaded.config.pubsub,
            ai_provider=ai,
            ai_settings=loaded.config.ai,
            notification_port=notifications,
            notifications_settings=loaded.config.notifications,
            startup_registration_port=startup_registration,
            role=role,
        ),
    )
