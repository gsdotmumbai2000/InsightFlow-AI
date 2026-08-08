"""Immutable typed configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AppEnvironment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecretStoreBackend(StrEnum):
    """Configured secret-store backend."""

    MEMORY = "memory"
    UNAVAILABLE = "unavailable"
    WINDOWS = "windows"


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    """Core application identity and environment settings."""

    environment: AppEnvironment
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Logging behavior settings."""

    level: LogLevel
    console_enabled: bool
    file_enabled: bool
    max_bytes: int
    backup_count: int


@dataclass(frozen=True, slots=True)
class StorageSettings:
    """Filesystem location settings.

    ``None`` values mean "use the platform-appropriate default".
    """

    data_dir: Path | None
    log_dir: Path | None


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    """Non-secret security/runtime settings."""

    secret_store_backend: SecretStoreBackend


@dataclass(frozen=True, slots=True)
class GmailSettings:
    """Non-secret Gmail OAuth client configuration.

    User access/refresh tokens are stored in SecretStore, never here.
    Client secret may be supplied via env for desktop apps or a secrets file
    path; prefer SecretStore / untracked client-secrets JSON over committing
    secrets.
    """

    client_id: str | None
    client_secret: str | None
    client_secrets_file: Path | None
    oauth_local_port: int


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Root immutable application configuration."""

    application: ApplicationSettings
    logging: LoggingSettings
    storage: StorageSettings
    security: SecuritySettings
    gmail: GmailSettings
