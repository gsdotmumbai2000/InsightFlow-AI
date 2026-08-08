"""Topics management view."""

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

from insightflow.presentation.dialogs.create_topic_dialog import CreateTopicDialog
from insightflow.presentation.viewmodels.topics_view_model import (
    TopicsViewModel,
    TopicsViewState,
)
from insightflow.presentation.widgets.page_helpers import (
    clear_banners,
    configure_table,
    make_banners,
    make_page_header,
    set_table_row,
    show_error,
    show_info,
    vertical_page,
)


class TopicsView(QWidget):
    def __init__(
        self, view_model: TopicsViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.setObjectName("TopicsView")
        self.setAccessibleName("Topics page")
        self._updating = False

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Topics", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

        actions = QHBoxLayout()
        self._create = QPushButton("Create topic")
        self._create.setObjectName("PrimaryButton")
        self._create.setAccessibleName("Create topic")
        self._create.clicked.connect(self._on_create)
        self._enable = QPushButton("Enable")
        self._disable = QPushButton("Disable")
        self._pause = QPushButton("Pause")
        self._resume = QPushButton("Resume")
        for button, slot in (
            (self._enable, self._on_enable),
            (self._disable, self._on_disable),
            (self._pause, self._on_pause),
            (self._resume, self._on_resume),
        ):
            button.clicked.connect(slot)
            actions.addWidget(button)
        actions.insertWidget(0, self._create)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._empty = QLabel()
        self._empty.setObjectName("EmptyState")
        layout.addWidget(self._empty)

        self._table = QTableWidget(0, 4)
        self._table.setObjectName("TopicsTable")
        self._table.setHorizontalHeaderLabels(
            ["Name", "Description", "Status", "AI profile"]
        )
        configure_table(self._table)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        self.apply_state(self._vm.load())

    def apply_state(self, state: TopicsViewState) -> None:
        clear_banners(self)
        if state.error_message:
            show_error(self, state.error_message)
        if state.info_message:
            show_info(self, state.info_message)
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
                    [row.name, row.description, row.status, row.ai_profile],
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
        topic_id = items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(topic_id, str):
            self.apply_state(self._vm.select(topic_id))

    def _on_create(self) -> None:
        dialog = CreateTopicDialog(self)
        if dialog.exec() != CreateTopicDialog.DialogCode.Accepted:
            return
        data = dialog.form_data()
        source_type = "GENERIC"
        source_id = "local"
        source_identifier = None
        if data.gmail_label_id:
            status = self._vm._use_cases.get_gmail_connection_status.execute()
            if status.account is None:
                state = self._vm.load()
                from insightflow.presentation.viewmodels.topics_view_model import (
                    TopicsViewState,
                )

                self.apply_state(
                    TopicsViewState(
                        rows=state.rows,
                        selected_id=state.selected_id,
                        error_message="Connect Gmail before mapping a label.",
                    )
                )
                return
            source_type = "GMAIL"
            source_id = status.account.account_id
            source_identifier = data.gmail_label_id
        self.apply_state(
            self._vm.create_topic(
                name=data.name,
                description=data.description or None,
                ai_profile_id=data.ai_profile_id or None,
                source_type=source_type,
                source_id=source_id,
                source_identifier=source_identifier,
            )
        )

    def _on_enable(self) -> None:
        self.apply_state(self._vm.enable())

    def _on_disable(self) -> None:
        self.apply_state(self._vm.disable())

    def _on_pause(self) -> None:
        self.apply_state(self._vm.pause())

    def _on_resume(self) -> None:
        self.apply_state(self._vm.resume())
