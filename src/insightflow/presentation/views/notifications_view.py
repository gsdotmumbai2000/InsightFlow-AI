"""In-application notifications history view."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from insightflow.presentation.viewmodels.notifications_view_model import (
    NotificationsViewModel,
    NotificationsViewState,
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


class NotificationsView(QWidget):
    def __init__(
        self,
        view_model: NotificationsViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.setObjectName("NotificationsView")
        self.setAccessibleName("Notifications page")
        self._updating = False

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Notifications", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

        actions = QHBoxLayout()
        self._displayed = QPushButton("Mark displayed")
        self._dismissed = QPushButton("Mark dismissed")
        self._displayed.clicked.connect(
            lambda: self.apply_state(self._vm.mark_displayed())
        )
        self._dismissed.clicked.connect(
            lambda: self.apply_state(self._vm.mark_dismissed())
        )
        actions.addWidget(self._displayed)
        actions.addWidget(self._dismissed)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._empty = QLabel()
        self._empty.setObjectName("EmptyState")
        layout.addWidget(self._empty)

        self._table = QTableWidget(0, 5)
        self._table.setObjectName("NotificationsTable")
        self._table.setHorizontalHeaderLabels(
            ["Title", "Summary", "Priority", "Status", "Created"]
        )
        configure_table(self._table)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        self.apply_state(self._vm.load())

    def apply_state(self, state: NotificationsViewState) -> None:
        clear_banners(self)
        if state.error_message:
            show_error(self, state.error_message)
        self._updating = True
        try:
            self._empty.setText(state.empty_message or "")
            self._table.setRowCount(0)
            selected_row = -1
            for index, row in enumerate(state.rows):
                self._table.insertRow(index)
                set_table_row(
                    self._table,
                    index,
                    [
                        row.title,
                        row.summary,
                        row.priority,
                        row.status,
                        row.created_at,
                    ],
                    user_data=row.id,
                )
                if state.selected_id == row.id:
                    selected_row = index
            if selected_row >= 0:
                self._table.selectRow(selected_row)
        finally:
            self._updating = False

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self._table.selectedItems()
        if not items:
            return
        notification_id = items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(notification_id, str):
            self.apply_state(self._vm.select(notification_id))
