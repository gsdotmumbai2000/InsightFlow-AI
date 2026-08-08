"""Structured logging formatters and filters."""

from __future__ import annotations

import logging
import re
from typing import Final

from insightflow.shared.correlation import get_correlation_id

_SECRET_ASSIGNMENT: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b("
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"password|client[_-]?secret|secret|authorization"
    r")\b\s*[:=]\s*.+"
)
_BEARER_TOKEN: Final[re.Pattern[str]] = re.compile(r"(?i)\bbearer\s+[a-z0-9\-._~+/]+=*")


def redact_secrets(message: str) -> str:
    """Redact common secret-like tokens from a log message."""
    redacted = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        message,
    )
    return _BEARER_TOKEN.sub("Bearer [REDACTED]", redacted)


class CorrelationIdFilter(logging.Filter):
    """Inject the current correlation ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class StructuredFormatter(logging.Formatter):
    """Consistent structured text log format with secret redaction."""

    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03d"

    def __init__(self) -> None:
        super().__init__(
            fmt=(
                "%(asctime)s %(levelname)s [%(name)s] "
                "correlation_id=%(correlation_id)s %(message)s"
            )
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id() or "-"
        original_msg = record.msg
        original_args = record.args
        try:
            rendered = record.getMessage()
            record.msg = redact_secrets(rendered)
            record.args = ()
            return super().format(record)
        finally:
            record.msg = original_msg
            record.args = original_args
