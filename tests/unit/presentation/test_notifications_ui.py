"""Notifications UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidget
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import EventId, Notification, Priority
from insightflow.presentation.views.notifications_view import NotificationsView
from insightflow.presentation.windows.main_window import MainWindow


def _notifications(main_window: MainWindow) -> NotificationsView:
    main_window.navigate_to("notifications")
    page = main_window._pages["notifications"]
    assert isinstance(page, NotificationsView)
    return page


def _cell(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    assert item is not None
    return item.text()


def test_notification_list_displayed_dismissed_empty(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    memory_store: InMemoryStore,
) -> None:
    page = _notifications(main_window)
    page.refresh()
    assert "No notifications" in page._empty.text()

    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="n-evt",
            title="Notify source",
        )
    )
    notification = Notification.create(
        event_id=EventId(event.id),
        priority=Priority.HIGH,
        title="Alert title",
        summary="Alert summary",
    )
    with memory_store.unit_of_work_factory() as uow:
        uow.notifications.add(notification)
        uow.commit()

    page.refresh()
    qapp.processEvents()
    assert page._table.rowCount() == 1
    page._table.selectRow(0)
    qapp.processEvents()

    page.apply_state(page._vm.mark_displayed())
    assert _cell(page._table, 0, 3) == "DISPLAYED"

    page.apply_state(page._vm.mark_dismissed())
    assert _cell(page._table, 0, 3) == "DISMISSED"
