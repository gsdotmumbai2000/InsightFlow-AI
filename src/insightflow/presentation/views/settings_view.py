"""Settings page with Gmail connection and label mapping."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from insightflow.presentation.viewmodels.settings_view_model import (
    SettingsViewModel,
    SettingsViewState,
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


class _ConnectWorker(QObject):
    finished_ok = Signal(object)
    finished_err = Signal(str)

    def __init__(self, view_model: SettingsViewModel) -> None:
        super().__init__()
        self._vm = view_model

    def run(self) -> None:
        state = self._vm.connect_gmail()
        if state.error_message:
            self.finished_err.emit(state.error_message)
        else:
            self.finished_ok.emit(state)


class SettingsView(QWidget):
    def __init__(
        self, view_model: SettingsViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._thread: QThread | None = None
        self._worker: _ConnectWorker | None = None
        self.setObjectName("SettingsView")
        self.setAccessibleName("Settings page")

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Settings", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

        note = QLabel(
            "Safe configuration summary. Secrets and OAuth credentials are never shown."
        )
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._table = QTableWidget(0, 2)
        self._table.setObjectName("SettingsTable")
        self._table.setHorizontalHeaderLabels(["Setting", "Value"])
        configure_table(self._table)
        layout.addWidget(self._table, stretch=1)

        gmail_title = QLabel("Gmail")
        gmail_title.setObjectName("SectionTitle")
        layout.addWidget(gmail_title)

        self._gmail_status = QLabel()
        self._gmail_status.setObjectName("GmailStatusLabel")
        self._gmail_status.setWordWrap(True)
        layout.addWidget(self._gmail_status)

        actions = QHBoxLayout()
        self._connect = QPushButton("Connect Gmail")
        self._connect.setObjectName("PrimaryButton")
        self._connect.setAccessibleName("Connect Gmail")
        self._disconnect = QPushButton("Disconnect")
        self._disconnect.setAccessibleName("Disconnect Gmail")
        self._refresh_labels = QPushButton("Refresh labels")
        self._refresh_labels.setAccessibleName("Refresh Gmail labels")
        self._connect.clicked.connect(self._on_connect)
        self._disconnect.clicked.connect(self._on_disconnect)
        self._refresh_labels.clicked.connect(self._on_refresh_labels)
        actions.addWidget(self._connect)
        actions.addWidget(self._disconnect)
        actions.addWidget(self._refresh_labels)
        actions.addStretch(1)
        layout.addLayout(actions)

        filter_row = QHBoxLayout()
        self._label_filter = QLineEdit()
        self._label_filter.setObjectName("GmailLabelFilter")
        self._label_filter.setPlaceholderText("Filter labels…")
        self._label_filter.setAccessibleName("Filter Gmail labels")
        self._label_filter.textChanged.connect(self._apply_label_filter)
        filter_row.addWidget(self._label_filter)
        layout.addLayout(filter_row)

        lists = QHBoxLayout()
        labels_col = QVBoxLayout()
        labels_col.addWidget(QLabel("Gmail labels"))
        self._labels = QListWidget()
        self._labels.setObjectName("GmailLabelsList")
        self._labels.setAccessibleName("Gmail labels")
        self._labels.currentItemChanged.connect(self._on_label_selected)
        labels_col.addWidget(self._labels)
        lists.addLayout(labels_col, stretch=1)

        topics_col = QVBoxLayout()
        topics_col.addWidget(QLabel("Topics"))
        self._topics = QListWidget()
        self._topics.setObjectName("GmailTopicsList")
        self._topics.setAccessibleName("Topics for Gmail mapping")
        self._topics.currentItemChanged.connect(self._on_topic_selected)
        topics_col.addWidget(self._topics)
        lists.addLayout(topics_col, stretch=1)
        layout.addLayout(lists, stretch=1)

        self._map_button = QPushButton("Map selected label to topic")
        self._map_button.setAccessibleName("Map Gmail label to topic")
        self._map_button.clicked.connect(self._on_map)
        layout.addWidget(self._map_button)

        self._all_labels: list[tuple[str, str]] = []
        self._applying_state = False

    def refresh(self) -> None:
        self.apply_state(self._vm.load())

    def apply_state(self, state: SettingsViewState) -> None:
        self._applying_state = True
        try:
            clear_banners(self)
            if state.error_message:
                show_error(self, state.error_message)
            if state.info_message:
                show_info(self, state.info_message)

            self._table.setRowCount(0)
            for index, (key, value) in enumerate(state.rows):
                self._table.insertRow(index)
                set_table_row(self._table, index, [key, value])

            self._gmail_status.setText(
                f"Status: {state.gmail_status}\n"
                f"Account: {state.gmail_account}\n"
                f"{state.gmail_message}"
            )
            connected = state.gmail_status == "CONNECTED"
            self._connect.setEnabled(not state.busy and not connected)
            self._disconnect.setEnabled(not state.busy and connected)
            self._refresh_labels.setEnabled(not state.busy and connected)
            self._map_button.setEnabled(not state.busy and connected)

            self._all_labels = [(label.label_id, label.name) for label in state.labels]
            self._apply_label_filter(
                self._label_filter.text(),
                selected_label_id=state.selected_label_id,
            )

            self._topics.blockSignals(True)
            self._topics.clear()
            selected_topic_row = -1
            for index, (topic_id, topic_name) in enumerate(state.topics):
                item = QListWidgetItem(topic_name)
                item.setData(Qt.ItemDataRole.UserRole, topic_id)
                self._topics.addItem(item)
                if state.selected_topic_id == topic_id:
                    selected_topic_row = index
            if selected_topic_row >= 0:
                self._topics.setCurrentRow(selected_topic_row)
            self._topics.blockSignals(False)
        finally:
            self._applying_state = False

    def _apply_label_filter(
        self,
        text: str,
        *,
        selected_label_id: str | None = None,
    ) -> None:
        needle = text.strip().lower()
        preferred = selected_label_id
        if preferred is None:
            current = self._labels.currentItem()
            if current is not None:
                raw = current.data(Qt.ItemDataRole.UserRole)
                if isinstance(raw, str):
                    preferred = raw

        self._labels.blockSignals(True)
        self._labels.clear()
        selected_row = -1
        row = 0
        for label_id, name in self._all_labels:
            if needle and needle not in name.lower():
                continue
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, label_id)
            self._labels.addItem(item)
            if preferred == label_id:
                selected_row = row
            row += 1
        if selected_row >= 0:
            self._labels.setCurrentRow(selected_row)
        self._labels.blockSignals(False)

    def _on_connect(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self.apply_state(self._vm.set_busy(True))
        self._thread = QThread(self)
        self._worker = _ConnectWorker(self._vm)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished_ok.connect(self._on_connect_ok)
        self._worker.finished_err.connect(self._on_connect_err)
        self._worker.finished_ok.connect(self._thread.quit)
        self._worker.finished_err.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_connect_ok(self, state: object) -> None:
        if isinstance(state, SettingsViewState):
            self.apply_state(state)

    def _on_connect_err(self, message: str) -> None:
        state = self._vm.set_busy(False)
        self.apply_state(
            SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                error_message=message,
            )
        )

    def _cleanup_thread(self) -> None:
        self._worker = None
        self._thread = None

    def _on_disconnect(self) -> None:
        self.apply_state(self._vm.disconnect_gmail())

    def _on_refresh_labels(self) -> None:
        self.apply_state(self._vm.refresh_labels())

    def _on_label_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if self._applying_state or current is None:
            return
        label_id = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(label_id, str):
            self._vm.select_label(label_id)

    def _on_topic_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if self._applying_state or current is None:
            return
        topic_id = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(topic_id, str):
            self._vm.select_topic(topic_id)

    def _on_map(self) -> None:
        self.apply_state(self._vm.map_selected_label_to_topic())
