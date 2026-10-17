"""Notification use cases."""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.mappers import notification_to_dto
from insightflow.application.dto.models import NotificationDto
from insightflow.application.exceptions import (
    ApplicationValidationError,
    NotificationNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import NotificationId


class ClearAllNotificationsUseCase:
    """Delete every notification; returns how many were deleted."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self) -> int:
        with use_case_scope("ClearAllNotifications"):

            def _run() -> int:
                with unit_of_work_scope(self._uow_factory) as uow:
                    deleted = uow.notifications.delete_all()
                    uow.commit()
                    return deleted

            return run_mutating(_run)


class GetNotificationUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, notification_id: str) -> NotificationDto:
        with (
            use_case_scope("GetNotification"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            notification = uow.notifications.get(NotificationId(notification_id))
            if notification is None:
                raise NotificationNotFoundError(
                    f"Notification not found: {notification_id}"
                )
            return notification_to_dto(notification)


class ListRecentNotificationsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, *, limit: int = 50) -> list[NotificationDto]:
        with (
            use_case_scope("ListRecentNotifications"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            if limit < 1:
                raise ApplicationValidationError("limit must be >= 1")
            items = uow.notifications.list_recent(limit=limit)
            return [notification_to_dto(item) for item in items]


class MarkNotificationDisplayedUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, notification_id: str) -> NotificationDto:
        return _transition_notification(self._uow_factory, notification_id, "displayed")


class MarkNotificationDismissedUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, notification_id: str) -> NotificationDto:
        return _transition_notification(self._uow_factory, notification_id, "dismissed")


def _transition_notification(
    uow_factory: Callable[[], UnitOfWork],
    notification_id: str,
    action: str,
) -> NotificationDto:
    with use_case_scope(f"MarkNotification{action.title()}"):

        def _run() -> NotificationDto:
            with unit_of_work_scope(uow_factory) as uow:
                notification = uow.notifications.get(NotificationId(notification_id))
                if notification is None:
                    raise NotificationNotFoundError(
                        f"Notification not found: {notification_id}"
                    )
                if action == "displayed":
                    notification.mark_displayed()
                elif action == "dismissed":
                    notification.mark_dismissed()
                else:
                    raise ApplicationValidationError(
                        f"Unknown notification action: {action}"
                    )
                uow.notifications.update(notification)
                uow.commit()
                return notification_to_dto(notification)

        return run_mutating(_run)
