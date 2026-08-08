"""Dashboard presentation state and use-case orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.application.dto.models import (
    DashboardSummaryDto,
    IntelligenceEventDto,
    NotificationDto,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash, format_timestamp


@dataclass(frozen=True, slots=True)
class DashboardEventRow:
    priority: str
    title: str
    status: str
    received_at: str


@dataclass(frozen=True, slots=True)
class DashboardNotificationRow:
    title: str
    priority: str
    status: str
    created_at: str


@dataclass(frozen=True, slots=True)
class DashboardViewState:
    app_name: str
    app_status: str
    monitoring_status: str
    total_topic_count: int
    enabled_topic_count: int
    recent_event_count: int
    high_priority_event_count: int
    pending_notification_count: int
    recent_events: tuple[DashboardEventRow, ...]
    recent_notifications: tuple[DashboardNotificationRow, ...]
    notes: tuple[str, ...]
    error_message: str | None = None


class DashboardViewModel:
    def __init__(
        self,
        use_cases: ApplicationUseCases,
        *,
        app_name: str,
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._app_name = app_name
        self._executor = executor or UiExecutor()

    def load(self) -> DashboardViewState:
        try:
            summary = self._executor.run(
                lambda: self._use_cases.get_dashboard_summary.execute()
            )
            return self._to_state(summary)
        except Exception as exc:
            from insightflow.presentation.errors import user_message_for_error

            return DashboardViewState(
                app_name=self._app_name,
                app_status="Running",
                monitoring_status="Not configured",
                total_topic_count=0,
                enabled_topic_count=0,
                recent_event_count=0,
                high_priority_event_count=0,
                pending_notification_count=0,
                recent_events=(),
                recent_notifications=(),
                notes=(),
                error_message=user_message_for_error(exc),
            )

    def _to_state(self, summary: DashboardSummaryDto) -> DashboardViewState:
        monitoring = summary.monitoring_status or "Not configured"
        return DashboardViewState(
            app_name=self._app_name,
            app_status="Running",
            monitoring_status=monitoring,
            total_topic_count=summary.total_topic_count,
            enabled_topic_count=summary.enabled_topic_count,
            recent_event_count=summary.recent_event_count,
            high_priority_event_count=summary.high_priority_event_count,
            pending_notification_count=summary.pending_notification_count,
            recent_events=tuple(
                self._event_row(event) for event in summary.recent_events
            ),
            recent_notifications=tuple(
                self._notification_row(item) for item in summary.recent_notifications
            ),
            notes=summary.notes,
        )

    @staticmethod
    def _event_row(event: IntelligenceEventDto) -> DashboardEventRow:
        return DashboardEventRow(
            priority=display_or_dash(event.priority),
            title=display_or_dash(event.title),
            status=event.status,
            received_at=format_timestamp(event.received_at),
        )

    @staticmethod
    def _notification_row(item: NotificationDto) -> DashboardNotificationRow:
        return DashboardNotificationRow(
            title=item.title,
            priority=item.priority,
            status=item.status,
            created_at=format_timestamp(item.created_at),
        )
