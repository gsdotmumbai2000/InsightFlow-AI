"""Dashboard summary use case."""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope, use_case_scope
from insightflow.application.commands.monitoring import GetMonitoringStatusUseCase
from insightflow.application.dto.mappers import event_to_dto, notification_to_dto
from insightflow.application.dto.models import DashboardSummaryDto
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    AIAnalysisStatus,
    EventProcessingStatus,
    Priority,
)

_UNPROCESSED_STATUSES = frozenset(
    {
        EventProcessingStatus.RECEIVED,
        EventProcessingStatus.VALIDATING,
        EventProcessingStatus.NORMALIZED,
        EventProcessingStatus.TOPIC_RESOLVED,
        EventProcessingStatus.DEDUPLICATING,
        EventProcessingStatus.AI_PENDING,
        EventProcessingStatus.AI_PROCESSING,
        EventProcessingStatus.RETRY_PENDING,
    }
)

_HIGH_PRIORITIES = frozenset({Priority.HIGH, Priority.CRITICAL})


class GetDashboardSummaryUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        monitoring_status: GetMonitoringStatusUseCase | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._monitoring_status = monitoring_status

    def execute(
        self,
        *,
        recent_limit: int = 10,
        analysis_scan_limit: int = 100,
    ) -> DashboardSummaryDto:
        monitoring_status = self._resolve_monitoring_status()
        with (
            use_case_scope("GetDashboardSummary"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            topics = uow.topics.list_all()
            enabled_topics = uow.topics.list_enabled()
            recent_events = uow.events.list_recent(limit=recent_limit)
            # Bounded scan for aggregate counts (no unbounded load).
            scanned_events = uow.events.list_recent(limit=analysis_scan_limit)
            recent_notifications = uow.notifications.list_recent(limit=recent_limit)
            pending_notifications = uow.notifications.list_pending()

            high_priority = sum(
                1 for event in scanned_events if event.priority in _HIGH_PRIORITIES
            )
            unprocessed = sum(
                1 for event in scanned_events if event.status in _UNPROCESSED_STATUSES
            )
            completed_analyses = 0
            for event in scanned_events:
                analysis = uow.analyses.find_latest_by_event(event.id)
                if (
                    analysis is not None
                    and analysis.status is AIAnalysisStatus.COMPLETED
                ):
                    completed_analyses += 1

            notes = (
                "Aggregate counts are derived from a bounded recent-event "
                f"scan (limit={analysis_scan_limit}).",
            )
            return DashboardSummaryDto(
                enabled_topic_count=len(enabled_topics),
                total_topic_count=len(topics),
                recent_event_count=len(recent_events),
                high_priority_event_count=high_priority,
                unprocessed_event_count=unprocessed,
                pending_notification_count=len(pending_notifications),
                completed_analysis_recent_count=completed_analyses,
                monitoring_status=monitoring_status,
                recent_events=tuple(event_to_dto(e) for e in recent_events),
                recent_notifications=tuple(
                    notification_to_dto(n) for n in recent_notifications
                ),
                notes=notes,
            )

    def _resolve_monitoring_status(self) -> str | None:
        """Real-time monitoring status for the connected Gmail account.

        Delegates entirely to ``GetMonitoringStatusUseCase`` — the single
        place that reconciles a persisted ``RUNNING``/``STARTING`` status
        against actual worker liveness (see its docstring) — so Dashboard
        and Settings can never disagree, and "Running" is never reported
        here unless a worker is genuinely alive in this process.
        ``None`` (rendered "Not configured") when Gmail is not connected,
        monitoring has never been started, or no monitoring-status use
        case was wired in (e.g. a minimal test double).
        """
        if self._monitoring_status is None:
            return None
        status = self._monitoring_status.execute()
        if status.status == "NOT_CONFIGURED":
            return None
        return status.status
