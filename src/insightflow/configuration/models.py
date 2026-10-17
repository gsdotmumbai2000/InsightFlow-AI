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
class PubSubSettings:
    """Non-secret Gmail real-time monitoring configuration (Phase 10).

    ``project_id``/``topic``/``subscription`` identify user-provisioned
    Google Cloud resources (see docs/17_Phase10_Gmail_Realtime_Monitoring_Notes.md);
    InsightFlow never creates them. Pub/Sub subscriber credentials are a
    separate OAuth-derived token held in SecretStore, never here.
    """

    project_id: str | None
    topic: str | None
    subscription: str | None
    history_batch_size: int
    history_page_size: int
    full_sync_max_messages: int
    watch_renewal_margin_hours: float
    pull_max_messages: int
    idle_poll_seconds: float

    @property
    def is_configured(self) -> bool:
        return bool(self.project_id and self.topic and self.subscription)


@dataclass(frozen=True, slots=True)
class AISettings:
    """Non-secret AI analysis configuration (Phase 11).

    AWS credentials are resolved via boto3's default credential chain
    (environment, shared config/credentials files, or an IAM role) and are
    never read, stored, or logged by InsightFlow itself.
    """

    enabled: bool
    automatic_analysis_enabled: bool
    provider: str
    region: str | None
    model_id: str
    timeout_seconds: float
    max_retries: int
    max_input_chars: int
    max_output_tokens: int
    temperature: float
    queue_max_size: int

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.model_id)


@dataclass(frozen=True, slots=True)
class NotificationsSettings:
    """Non-secret Windows toast notification configuration (Phase 12).

    Notifications never carry secrets — only a safe title/body/event id.
    """

    enabled: bool


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Root immutable application configuration."""

    application: ApplicationSettings
    logging: LoggingSettings
    storage: StorageSettings
    security: SecuritySettings
    gmail: GmailSettings
    pubsub: PubSubSettings
    ai: AISettings
    notifications: NotificationsSettings
