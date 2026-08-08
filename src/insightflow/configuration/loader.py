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
    AppConfig,
    AppEnvironment,
    ApplicationSettings,
    GmailSettings,
    LoggingSettings,
    LogLevel,
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
    )
