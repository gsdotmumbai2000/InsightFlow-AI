"""Notifications page presentation state."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.application.dto.models import NotificationDto
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash, format_timestamp


@dataclass(frozen=True, slots=True)
class NotificationRow:
    id: str
    title: str
    summary: str
    priority: str
    status: str
    created_at: str


@dataclass(frozen=True, slots=True)
class NotificationsViewState:
    rows: tuple[NotificationRow, ...]
    selected_id: str | None = None
    error_message: str | None = None
    empty_message: str | None = None


class NotificationsViewModel:
    def __init__(
        self,
        use_cases: ApplicationUseCases,
        *,
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._executor = executor or UiExecutor()
        self._selected_id: str | None = None

    def load(self, *, selected_id: str | None = None) -> NotificationsViewState:
        if selected_id is not None:
            self._selected_id = selected_id
        try:
            items = self._executor.run(
                lambda: self._use_cases.list_recent_notifications.execute(limit=100)
            )
        except Exception as exc:
            return NotificationsViewState(
                rows=(),
                error_message=user_message_for_error(exc),
            )
        rows = tuple(self._row(item) for item in items)
        if self._selected_id and self._selected_id not in {row.id for row in rows}:
            self._selected_id = None
        return NotificationsViewState(
            rows=rows,
            selected_id=self._selected_id,
            empty_message=None if rows else "No notifications yet.",
        )

    def select(self, notification_id: str) -> NotificationsViewState:
        return self.load(selected_id=notification_id)

    def mark_displayed(self) -> NotificationsViewState:
        return self._mark("displayed")

    def mark_dismissed(self) -> NotificationsViewState:
        return self._mark("dismissed")

    def _mark(self, action: str) -> NotificationsViewState:
        if not self._selected_id:
            state = self.load()
            return NotificationsViewState(
                rows=state.rows,
                error_message="Select a notification first.",
            )
        notification_id = self._selected_id
        try:
            if action == "displayed":
                self._executor.run(
                    lambda: self._use_cases.mark_notification_displayed.execute(
                        notification_id
                    )
                )
            else:
                self._executor.run(
                    lambda: self._use_cases.mark_notification_dismissed.execute(
                        notification_id
                    )
                )
        except Exception as exc:
            state = self.load(selected_id=notification_id)
            return NotificationsViewState(
                rows=state.rows,
                selected_id=notification_id,
                error_message=user_message_for_error(exc),
            )
        return self.load(selected_id=notification_id)

    @staticmethod
    def _row(item: NotificationDto) -> NotificationRow:
        return NotificationRow(
            id=item.id,
            title=item.title,
            summary=display_or_dash(item.summary),
            priority=item.priority,
            status=item.status,
            created_at=format_timestamp(item.created_at),
        )
