"""Real-time monitoring application exceptions (Phase 10)."""

from __future__ import annotations

from insightflow.application.exceptions.application import ApplicationError


class MonitoringError(ApplicationError):
    """Base real-time monitoring application error."""


class MonitoringConfigurationError(MonitoringError):
    """Monitoring cannot start due to missing/invalid configuration."""


class MonitoringNotRunningError(MonitoringError):
    """An operation required active monitoring, but it is not running."""
