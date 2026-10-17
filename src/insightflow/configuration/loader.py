"""Load and validate typed application configuration."""

from __future__ import annotations

from pathlib import Path

from insightflow import __version__
from insightflow.configuration.env import (
    EnvironmentSource,
    MappingEnvironment,
    OsEnvironment,
    OverlayEnvironment,
    load_dotenv_file,
)
from insightflow.configuration.errors import ConfigurationError
from insightflow.configuration.models import (
    AISettings,
    AppConfig,
    AppEnvironment,
    ApplicationSettings,
    GmailSettings,
    LoggingSettings,
    LogLevel,
    NotificationsSettings,
    PubSubSettings,
    SecretStoreBackend,
    SecuritySettings,
    StorageSettings,
)

APP_NAME = "InsightFlow AI"

ENV_KEY = "INSIGHTFLOW_ENV"
LOG_LEVEL_KEY = "INSIGHTFLOW_LOG_LEVEL"
LOG_CONSOLE_KEY = "INSIGHTFLOW_LOG_CONSOLE"
LOG_FILE_KEY = "INSIGHTFLOW_LOG_FILE"
LOG_MAX_BYTES_KEY = "INSIGHTFLOW_LOG_MAX_BYTES"
LOG_BACKUP_COUNT_KEY = "INSIGHTFLOW_LOG_BACKUP_COUNT"
DATA_DIR_KEY = "INSIGHTFLOW_DATA_DIR"
LOG_DIR_KEY = "INSIGHTFLOW_LOG_DIR"
SECRET_STORE_KEY = "INSIGHTFLOW_SECRET_STORE"
GMAIL_CLIENT_ID_KEY = "INSIGHTFLOW_GMAIL_CLIENT_ID"
GMAIL_CLIENT_SECRET_KEY = "INSIGHTFLOW_GMAIL_CLIENT_SECRET"
GMAIL_CLIENT_SECRETS_FILE_KEY = "INSIGHTFLOW_GMAIL_CLIENT_SECRETS_FILE"
GMAIL_OAUTH_PORT_KEY = "INSIGHTFLOW_GMAIL_OAUTH_PORT"
PUBSUB_PROJECT_ID_KEY = "INSIGHTFLOW_GMAIL_PUBSUB_PROJECT_ID"
PUBSUB_TOPIC_KEY = "INSIGHTFLOW_GMAIL_PUBSUB_TOPIC"
PUBSUB_SUBSCRIPTION_KEY = "INSIGHTFLOW_GMAIL_PUBSUB_SUBSCRIPTION"
MONITORING_HISTORY_BATCH_SIZE_KEY = "INSIGHTFLOW_MONITORING_HISTORY_BATCH_SIZE"
MONITORING_HISTORY_PAGE_SIZE_KEY = "INSIGHTFLOW_MONITORING_HISTORY_PAGE_SIZE"
MONITORING_FULL_SYNC_MAX_MESSAGES_KEY = "INSIGHTFLOW_MONITORING_FULL_SYNC_MAX_MESSAGES"
MONITORING_WATCH_RENEWAL_MARGIN_HOURS_KEY = (
    "INSIGHTFLOW_MONITORING_WATCH_RENEWAL_MARGIN_HOURS"
)
MONITORING_PULL_MAX_MESSAGES_KEY = "INSIGHTFLOW_MONITORING_PULL_MAX_MESSAGES"
MONITORING_IDLE_POLL_SECONDS_KEY = "INSIGHTFLOW_MONITORING_IDLE_POLL_SECONDS"
AI_ENABLED_KEY = "INSIGHTFLOW_AI_ENABLED"
AI_AUTOMATIC_ANALYSIS_ENABLED_KEY = "INSIGHTFLOW_AI_AUTOMATIC_ANALYSIS_ENABLED"
AI_PROVIDER_KEY = "INSIGHTFLOW_AI_PROVIDER"
AI_REGION_KEY = "INSIGHTFLOW_AI_REGION"
AI_MODEL_ID_KEY = "INSIGHTFLOW_AI_MODEL_ID"
AI_TIMEOUT_SECONDS_KEY = "INSIGHTFLOW_AI_TIMEOUT_SECONDS"
AI_MAX_RETRIES_KEY = "INSIGHTFLOW_AI_MAX_RETRIES"
AI_MAX_INPUT_CHARS_KEY = "INSIGHTFLOW_AI_MAX_INPUT_CHARS"
AI_MAX_OUTPUT_TOKENS_KEY = "INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS"
AI_TEMPERATURE_KEY = "INSIGHTFLOW_AI_TEMPERATURE"
AI_QUEUE_MAX_SIZE_KEY = "INSIGHTFLOW_AI_QUEUE_MAX_SIZE"
NOTIFICATIONS_ENABLED_KEY = "INSIGHTFLOW_NOTIFICATIONS_ENABLED"

DEFAULT_AI_PROVIDER = "bedrock"
DEFAULT_AI_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _raw(source: EnvironmentSource, key: str) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _parse_bool(key: str, raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigurationError(
        f"Invalid boolean for {key}={raw!r}. "
        f"Expected one of: true, false, 1, 0, yes, no, on, off."
    )


def _parse_int(key: str, raw: str, *, minimum: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigurationError(
            f"Invalid integer for {key}={raw!r}. Expected a whole number."
        ) from exc
    if value < minimum:
        raise ConfigurationError(
            f"Invalid integer for {key}={raw!r}. Expected a value >= {minimum}."
        )
    return value


def _parse_environment(raw: str | None) -> AppEnvironment:
    if raw is None:
        return AppEnvironment.DEVELOPMENT
    try:
        return AppEnvironment(raw.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AppEnvironment)
        raise ConfigurationError(
            f"Invalid {ENV_KEY}={raw!r}. Expected one of: {allowed}."
        ) from exc


def _parse_log_level(raw: str | None) -> LogLevel:
    if raw is None:
        return LogLevel.INFO
    try:
        return LogLevel(raw.strip().upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in LogLevel)
        raise ConfigurationError(
            f"Invalid {LOG_LEVEL_KEY}={raw!r}. Expected one of: {allowed}."
        ) from exc


def _parse_secret_store(
    raw: str | None,
    *,
    environment: AppEnvironment,
) -> SecretStoreBackend:
    if raw is None:
        if environment is AppEnvironment.PRODUCTION:
            return SecretStoreBackend.WINDOWS
        return SecretStoreBackend.MEMORY
    try:
        backend = SecretStoreBackend(raw.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in SecretStoreBackend)
        raise ConfigurationError(
            f"Invalid {SECRET_STORE_KEY}={raw!r}. Expected one of: {allowed}."
        ) from exc

    if (
        environment is AppEnvironment.PRODUCTION
        and backend is SecretStoreBackend.MEMORY
    ):
        raise ConfigurationError(
            f"{SECRET_STORE_KEY}=memory is not allowed in production. "
            "Use INSIGHTFLOW_SECRET_STORE=windows."
        )
    return backend


def _parse_gmail_settings(source: EnvironmentSource) -> GmailSettings:
    secrets_file_raw = _raw(source, GMAIL_CLIENT_SECRETS_FILE_KEY)
    secrets_file: Path | None = None
    if secrets_file_raw is not None:
        secrets_file = Path(secrets_file_raw).expanduser()
        if not secrets_file.is_absolute():
            raise ConfigurationError(
                f"Invalid {GMAIL_CLIENT_SECRETS_FILE_KEY}={secrets_file_raw!r}. "
                "Path must be absolute."
            )

    port_raw = _raw(source, GMAIL_OAUTH_PORT_KEY)
    oauth_port = (
        0 if port_raw is None else _parse_int(GMAIL_OAUTH_PORT_KEY, port_raw, minimum=0)
    )
    return GmailSettings(
        client_id=_raw(source, GMAIL_CLIENT_ID_KEY),
        client_secret=_raw(source, GMAIL_CLIENT_SECRET_KEY),
        client_secrets_file=secrets_file,
        oauth_local_port=oauth_port,
    )


def _parse_float(key: str, raw: str, *, minimum: float) -> float:
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ConfigurationError(
            f"Invalid number for {key}={raw!r}. Expected a decimal number."
        ) from exc
    if value < minimum:
        raise ConfigurationError(
            f"Invalid number for {key}={raw!r}. Expected a value >= {minimum}."
        )
    return value


def _parse_pubsub_settings(source: EnvironmentSource) -> PubSubSettings:
    history_batch_raw = _raw(source, MONITORING_HISTORY_BATCH_SIZE_KEY)
    history_page_raw = _raw(source, MONITORING_HISTORY_PAGE_SIZE_KEY)
    full_sync_raw = _raw(source, MONITORING_FULL_SYNC_MAX_MESSAGES_KEY)
    renewal_margin_raw = _raw(source, MONITORING_WATCH_RENEWAL_MARGIN_HOURS_KEY)
    pull_max_raw = _raw(source, MONITORING_PULL_MAX_MESSAGES_KEY)
    idle_poll_raw = _raw(source, MONITORING_IDLE_POLL_SECONDS_KEY)
    return PubSubSettings(
        project_id=_raw(source, PUBSUB_PROJECT_ID_KEY),
        topic=_raw(source, PUBSUB_TOPIC_KEY),
        subscription=_raw(source, PUBSUB_SUBSCRIPTION_KEY),
        history_batch_size=(
            50
            if history_batch_raw is None
            else _parse_int(
                MONITORING_HISTORY_BATCH_SIZE_KEY, history_batch_raw, minimum=1
            )
        ),
        history_page_size=(
            100
            if history_page_raw is None
            else _parse_int(
                MONITORING_HISTORY_PAGE_SIZE_KEY, history_page_raw, minimum=1
            )
        ),
        full_sync_max_messages=(
            50
            if full_sync_raw is None
            else _parse_int(
                MONITORING_FULL_SYNC_MAX_MESSAGES_KEY, full_sync_raw, minimum=1
            )
        ),
        watch_renewal_margin_hours=(
            24.0
            if renewal_margin_raw is None
            else _parse_float(
                MONITORING_WATCH_RENEWAL_MARGIN_HOURS_KEY,
                renewal_margin_raw,
                minimum=0.1,
            )
        ),
        pull_max_messages=(
            10
            if pull_max_raw is None
            else _parse_int(MONITORING_PULL_MAX_MESSAGES_KEY, pull_max_raw, minimum=1)
        ),
        idle_poll_seconds=(
            5.0
            if idle_poll_raw is None
            else _parse_float(
                MONITORING_IDLE_POLL_SECONDS_KEY, idle_poll_raw, minimum=1.0
            )
        ),
    )


def _parse_ai_settings(source: EnvironmentSource) -> AISettings:
    enabled_raw = _raw(source, AI_ENABLED_KEY)
    automatic_raw = _raw(source, AI_AUTOMATIC_ANALYSIS_ENABLED_KEY)
    timeout_raw = _raw(source, AI_TIMEOUT_SECONDS_KEY)
    max_retries_raw = _raw(source, AI_MAX_RETRIES_KEY)
    max_input_chars_raw = _raw(source, AI_MAX_INPUT_CHARS_KEY)
    max_output_tokens_raw = _raw(source, AI_MAX_OUTPUT_TOKENS_KEY)
    temperature_raw = _raw(source, AI_TEMPERATURE_KEY)
    queue_max_size_raw = _raw(source, AI_QUEUE_MAX_SIZE_KEY)
    return AISettings(
        enabled=(
            False if enabled_raw is None else _parse_bool(AI_ENABLED_KEY, enabled_raw)
        ),
        automatic_analysis_enabled=(
            True
            if automatic_raw is None
            else _parse_bool(AI_AUTOMATIC_ANALYSIS_ENABLED_KEY, automatic_raw)
        ),
        provider=(_raw(source, AI_PROVIDER_KEY) or DEFAULT_AI_PROVIDER).lower(),
        region=_raw(source, AI_REGION_KEY),
        model_id=_raw(source, AI_MODEL_ID_KEY) or DEFAULT_AI_MODEL_ID,
        timeout_seconds=(
            30.0
            if timeout_raw is None
            else _parse_float(AI_TIMEOUT_SECONDS_KEY, timeout_raw, minimum=1.0)
        ),
        max_retries=(
            2
            if max_retries_raw is None
            else _parse_int(AI_MAX_RETRIES_KEY, max_retries_raw, minimum=0)
        ),
        max_input_chars=(
            12_000
            if max_input_chars_raw is None
            else _parse_int(AI_MAX_INPUT_CHARS_KEY, max_input_chars_raw, minimum=100)
        ),
        max_output_tokens=(
            1024
            if max_output_tokens_raw is None
            else _parse_int(AI_MAX_OUTPUT_TOKENS_KEY, max_output_tokens_raw, minimum=64)
        ),
        temperature=(
            0.2
            if temperature_raw is None
            else _parse_float(AI_TEMPERATURE_KEY, temperature_raw, minimum=0.0)
        ),
        queue_max_size=(
            100
            if queue_max_size_raw is None
            else _parse_int(AI_QUEUE_MAX_SIZE_KEY, queue_max_size_raw, minimum=1)
        ),
    )


def _parse_notifications_settings(source: EnvironmentSource) -> NotificationsSettings:
    enabled_raw = _raw(source, NOTIFICATIONS_ENABLED_KEY)
    return NotificationsSettings(
        enabled=(
            True
            if enabled_raw is None
            else _parse_bool(NOTIFICATIONS_ENABLED_KEY, enabled_raw)
        ),
    )


def _parse_optional_path(key: str, raw: str | None) -> Path | None:
    if raw is None:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ConfigurationError(
            f"Invalid {key}={raw!r}. Directory paths must be absolute."
        )
    return path


def discover_dotenv_path(*, start: Path | None = None) -> Path | None:
    """Find a ``.env`` file from the working directory or project root.

    Looks for ``.env`` in ``start`` (default: cwd), then walks parents until a
    directory containing both ``pyproject.toml`` and ``.env`` is found.
    """
    current = (start or Path.cwd()).resolve()
    direct = current / ".env"
    if direct.is_file():
        return direct
    for parent in (current, *current.parents):
        candidate = parent / ".env"
        if candidate.is_file() and (parent / "pyproject.toml").is_file():
            return candidate
    return None


def build_environment_source(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> EnvironmentSource:
    """Compose dotenv defaults under process environment overrides.

    When ``environ`` is omitted (normal app startup), a project ``.env`` is
    discovered automatically if ``dotenv_path`` is not provided. Tests that
    pass an explicit ``environ`` mapping are unaffected.
    """
    resolved = dotenv_path
    if resolved is None and environ is None:
        resolved = discover_dotenv_path()

    base: EnvironmentSource = MappingEnvironment({})
    if resolved is not None:
        base = MappingEnvironment(load_dotenv_file(resolved))
    overlay = environ if environ is not None else OsEnvironment()
    return OverlayEnvironment(base=base, overlay=overlay)


def load_config(
    *,
    environ: EnvironmentSource | None = None,
    dotenv_path: Path | None = None,
) -> AppConfig:
    """Load, parse, and validate immutable application configuration.

    Invalid values raise :class:`ConfigurationError` and are never silently
    replaced with defaults.
    """
    source = build_environment_source(environ=environ, dotenv_path=dotenv_path)

    environment = _parse_environment(_raw(source, ENV_KEY))
    log_level = _parse_log_level(_raw(source, LOG_LEVEL_KEY))

    console_raw = _raw(source, LOG_CONSOLE_KEY)
    file_raw = _raw(source, LOG_FILE_KEY)
    console_enabled = (
        True if console_raw is None else _parse_bool(LOG_CONSOLE_KEY, console_raw)
    )
    file_enabled = True if file_raw is None else _parse_bool(LOG_FILE_KEY, file_raw)

    max_bytes_raw = _raw(source, LOG_MAX_BYTES_KEY)
    backup_raw = _raw(source, LOG_BACKUP_COUNT_KEY)
    max_bytes = (
        5_000_000
        if max_bytes_raw is None
        else _parse_int(LOG_MAX_BYTES_KEY, max_bytes_raw, minimum=1)
    )
    backup_count = (
        3
        if backup_raw is None
        else _parse_int(LOG_BACKUP_COUNT_KEY, backup_raw, minimum=0)
    )

    secret_backend = _parse_secret_store(
        _raw(source, SECRET_STORE_KEY),
        environment=environment,
    )

    return AppConfig(
        application=ApplicationSettings(
            environment=environment,
            name=APP_NAME,
            version=__version__,
        ),
        logging=LoggingSettings(
            level=log_level,
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            max_bytes=max_bytes,
            backup_count=backup_count,
        ),
        storage=StorageSettings(
            data_dir=_parse_optional_path(DATA_DIR_KEY, _raw(source, DATA_DIR_KEY)),
            log_dir=_parse_optional_path(LOG_DIR_KEY, _raw(source, LOG_DIR_KEY)),
        ),
        security=SecuritySettings(secret_store_backend=secret_backend),
        gmail=_parse_gmail_settings(source),
        pubsub=_parse_pubsub_settings(source),
        ai=_parse_ai_settings(source),
        notifications=_parse_notifications_settings(source),
    )
