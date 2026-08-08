"""Bootstrap dependency factories."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

from insightflow.application.ports.gmail import GmailAuthenticator, GmailLabelProvider
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.ports.secret_store import SecretStore
from insightflow.application.use_cases import build_use_cases
from insightflow.bootstrap.container import AppContainer
from insightflow.configuration.diagnostics import collect_diagnostics
from insightflow.configuration.env import EnvironmentSource
from insightflow.configuration.models import AppConfig, SecretStoreBackend
from insightflow.configuration.provider import (
    ConfigurationProvider,
    LoadedConfiguration,
)
from insightflow.infrastructure.database.connection import connect
from insightflow.infrastructure.database.migrations import initialize_database
from insightflow.infrastructure.database.unit_of_work import SQLiteUnitOfWork
from insightflow.infrastructure.gmail.adapter import GoogleGmailAdapter
from insightflow.infrastructure.logging.setup import (
    configure_logging,
    get_logger,
    is_logging_configured,
)
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
) -> AppContainer:
    """Create the application dependency container.

    Optional gmail_* overrides are for tests (fake ports). Production uses
    GoogleGmailAdapter assembled here.
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
    authenticator: GmailAuthenticator = gmail_authenticator or gmail
    labels: GmailLabelProvider = gmail_labels or gmail

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
        ),
    )
