"""Logging foundation tests."""

from __future__ import annotations

import logging
from pathlib import Path

from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.loader import load_config
from insightflow.infrastructure.logging.formatters import redact_secrets
from insightflow.infrastructure.logging.setup import configure_logging, get_logger
from insightflow.shared.correlation import correlation_context


def test_logger_initialization_and_level(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_LOG_LEVEL": "WARNING",
                "INSIGHTFLOW_LOG_CONSOLE": "false",
                "INSIGHTFLOW_LOG_FILE": "true",
            }
        )
    )
    configure_logging(config.logging, tmp_path)
    logger = get_logger("unit.logging")
    assert logger.getEffectiveLevel() == logging.WARNING

    logger.warning("hello-warning")
    log_text = (tmp_path / "insightflow.log").read_text(encoding="utf-8")
    assert "hello-warning" in log_text
    assert "WARNING" in log_text


def test_correlation_id_appears_in_logs(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_LOG_CONSOLE": "false",
                "INSIGHTFLOW_LOG_FILE": "true",
            }
        )
    )
    configure_logging(config.logging, tmp_path)
    logger = get_logger("unit.correlation")
    with correlation_context("abc123correlation"):
        logger.info("correlated-event")
    log_text = (tmp_path / "insightflow.log").read_text(encoding="utf-8")
    assert "correlation_id=abc123correlation" in log_text
    assert "correlated-event" in log_text


def test_exceptions_are_logged(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_LOG_CONSOLE": "false",
                "INSIGHTFLOW_LOG_FILE": "true",
            }
        )
    )
    configure_logging(config.logging, tmp_path)
    logger = get_logger("unit.exceptions")
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("operation failed")
    log_text = (tmp_path / "insightflow.log").read_text(encoding="utf-8")
    assert "operation failed" in log_text
    assert "RuntimeError: boom" in log_text
    assert "Traceback" in log_text


def test_secrets_are_not_emitted(tmp_path: Path) -> None:
    config = load_config(
        environ=MappingEnvironment(
            {
                "INSIGHTFLOW_LOG_CONSOLE": "false",
                "INSIGHTFLOW_LOG_FILE": "true",
            }
        )
    )
    configure_logging(config.logging, tmp_path)
    logger = get_logger("unit.secrets")
    logger.info("api_key=%s password=%s", "super-secret", "hunter2")
    logger.info("Authorization: Bearer abcdef123456")
    log_text = (tmp_path / "insightflow.log").read_text(encoding="utf-8")
    assert "super-secret" not in log_text
    assert "hunter2" not in log_text
    assert "abcdef123456" not in log_text
    assert "[REDACTED]" in log_text


def test_redact_secrets_helper() -> None:
    assert "tokensecret" not in redact_secrets("access_token=tokensecret")
    assert "[REDACTED]" in redact_secrets("access_token=tokensecret")
