"""Dashboard page view."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from insightflow.presentation.viewmodels.dashboard_view_model import (
    DashboardViewModel,
    DashboardViewState,
)
from insightflow.presentation.widgets.page_helpers import (
    clear_banners,
    configure_table,
    make_banners,
    make_page_header,
    set_table_row,
    show_error,
    vertical_page,
)


class DashboardView(QWidget):
    def __init__(
        self, view_model: DashboardViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.setObjectName("DashboardView")
        self.setAccessibleName("Dashboard page")

        self._page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._page)

        header, _ = make_page_header("Dashboard", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

        self._summary = QLabel()
        self._summary.setObjectName("DashboardSummary")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        events_title = QLabel("Recent intelligence events")
        events_title.setObjectName("SectionTitle")
        layout.addWidget(events_title)
        self._events = QTableWidget(0, 4)
        self._events.setObjectName("DashboardEventsTable")
        self._events.setHorizontalHeaderLabels(
            ["Priority", "Title", "Status", "Received"]
        )
        configure_table(self._events)
        layout.addWidget(self._events, stretch=1)

        notes_title = QLabel("Recent notifications")
        notes_title.setObjectName("SectionTitle")
        layout.addWidget(notes_title)
        self._notifications = QTableWidget(0, 4)
        self._notifications.setObjectName("DashboardNotificationsTable")
        self._notifications.setHorizontalHeaderLabels(
            ["Title", "Priority", "Status", "Created"]
        )
        configure_table(self._notifications)
        layout.addWidget(self._notifications, stretch=1)

        self._notes = QLabel()
        self._notes.setObjectName("MutedLabel")
        self._notes.setWordWrap(True)
        layout.addWidget(self._notes)

    def refresh(self) -> None:
        self.apply_state(self._vm.load())

    def apply_state(self, state: DashboardViewState) -> None:
        clear_banners(self)
        if state.error_message:
            show_error(self, state.error_message)
        self._summary.setText(
            f"{state.app_name}\n"
            f"Application: {state.app_status}\n"
            f"Monitoring: {state.monitoring_status}\n"
            f"Topics: {state.total_topic_count} "
            f"({state.enabled_topic_count} enabled)\n"
            f"Recent events: {state.recent_event_count}\n"
            f"High priority: {state.high_priority_event_count}\n"
            f"Pending notifications: {state.pending_notification_count}"
        )
        self._events.setRowCount(0)
        for row_index, event_row in enumerate(state.recent_events):
            self._events.insertRow(row_index)
            set_table_row(
                self._events,
                row_index,
                [
                    event_row.priority,
                    event_row.title,
                    event_row.status,
                    event_row.received_at,
                ],
            )
        self._notifications.setRowCount(0)
        for row_index, notification_row in enumerate(state.recent_notifications):
            self._notifications.insertRow(row_index)
            set_table_row(
                self._notifications,
                row_index,
                [
                    notification_row.title,
                    notification_row.priority,
                    notification_row.status,
                    notification_row.created_at,
                ],
            )
        self._notes.setText("\n".join(state.notes) if state.notes else "")
