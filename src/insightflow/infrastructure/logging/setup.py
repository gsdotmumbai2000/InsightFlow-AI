"""Logging initialization for InsightFlow AI."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from insightflow.configuration.models import LoggingSettings
from insightflow.infrastructure.logging.formatters import (
    CorrelationIdFilter,
    StructuredFormatter,
)

_ROOT_LOGGER_NAME = "insightflow"
_configured = False


def is_logging_configured() -> bool:
    """Return whether InsightFlow logging has been initialized."""
    return _configured


def reset_logging_state() -> None:
    """Reset logging configuration state (intended for tests)."""
    global _configured
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _configured = False


def configure_logging(settings: LoggingSettings, log_dir: Path) -> None:
    """Configure structured console/file logging for the application."""
    global _configured

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(settings.level.value)
    logger.propagate = False

    formatter = StructuredFormatter()
    correlation_filter = CorrelationIdFilter()

    if settings.console_enabled:
        console = logging.StreamHandler()
        console.setLevel(settings.level.value)
        console.setFormatter(formatter)
        console.addFilter(correlation_filter)
        logger.addHandler(console)

    if settings.file_enabled:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_dir / "insightflow.log",
            maxBytes=settings.max_bytes,
            backupCount=settings.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(settings.level.value)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(correlation_filter)
        logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return an application logger under the InsightFlow logger hierarchy."""
    if name is None or name == _ROOT_LOGGER_NAME:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    if name.startswith(f"{_ROOT_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
