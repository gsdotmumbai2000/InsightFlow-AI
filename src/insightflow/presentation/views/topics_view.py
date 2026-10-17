"""Topics management view."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from insightflow.presentation.dialogs.create_ai_profile_dialog import (
    CreateAIProfileDialog,
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

_NOT_CONFIGURED_OPTION = "Not configured"


class _RetrieveMessagesWorker(QObject):
    """Runs Gmail message retrieval off the GUI thread (Phase 8)."""

    finished_ok = Signal(object)
    finished_err = Signal(str)

    def __init__(self, view_model: TopicsViewModel) -> None:
        super().__init__()
        self._vm = view_model

    def run(self) -> None:
        state = self._vm.retrieve_recent_messages()
        if state.error_message:
            self.finished_err.emit(state.error_message)
        else:
            self.finished_ok.emit(state)


class _SaveMessagesWorker(QObject):
    """Runs Gmail message ingestion off the GUI thread (Phase 9)."""

    finished_ok = Signal(object)
    finished_err = Signal(str)

    def __init__(self, view_model: TopicsViewModel) -> None:
        super().__init__()
        self._vm = view_model

    def run(self) -> None:
        state = self._vm.save_recent_messages()
        if state.error_message:
            self.finished_err.emit(state.error_message)
        else:
            self.finished_ok.emit(state)


class TopicsView(QWidget):
    def __init__(
        self, view_model: TopicsViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._thread: QThread | None = None
        self._worker: _RetrieveMessagesWorker | None = None
        self._save_thread: QThread | None = None
        self._save_worker: _SaveMessagesWorker | None = None
        self.setObjectName("TopicsView")
        self.setAccessibleName("Topics page")
        self._updating = False
        self._selected_source_type: str | None = None
        self._selected_topic_name: str | None = None
        self._selected_ai_profile_id: str | None = None

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
        self._retrieve = QPushButton("Retrieve recent messages")
        self._retrieve.setAccessibleName("Retrieve recent Gmail messages")
        self._retrieve.setEnabled(False)
        self._save = QPushButton("Save recent messages")
        self._save.setAccessibleName("Save recent Gmail messages as events")
        self._save.setEnabled(False)
        for button, slot in (
            (self._enable, self._on_enable),
            (self._disable, self._on_disable),
            (self._pause, self._on_pause),
            (self._resume, self._on_resume),
            (self._retrieve, self._on_retrieve),
            (self._save, self._on_save),
        ):
            button.clicked.connect(slot)
            actions.addWidget(button)
        actions.insertWidget(0, self._create)
        actions.addStretch(1)
        layout.addLayout(actions)

        ai_profile_row = QHBoxLayout()
        ai_profile_label = QLabel("AI Profile:")
        ai_profile_row.addWidget(ai_profile_label)
        self._ai_profile_combo = QComboBox()
        self._ai_profile_combo.setObjectName("TopicAiProfileCombo")
        self._ai_profile_combo.setAccessibleName("AI profile for the selected topic")
        self._ai_profile_combo.setEnabled(False)
        self._ai_profile_combo.currentIndexChanged.connect(self._on_ai_profile_selected)
        ai_profile_row.addWidget(self._ai_profile_combo, stretch=1)
        self._create_ai_profile = QPushButton("Create AI Profile")
        self._create_ai_profile.setObjectName("CreateAiProfileButton")
        self._create_ai_profile.setAccessibleName("Create AI profile")
        self._create_ai_profile.clicked.connect(self._on_create_ai_profile)
        self._edit_ai_profile = QPushButton("Edit AI Profile")
        self._edit_ai_profile.setObjectName("EditAiProfileButton")
        self._edit_ai_profile.setAccessibleName("Edit the selected AI profile")
        self._edit_ai_profile.setEnabled(False)
        self._edit_ai_profile.clicked.connect(self._on_edit_ai_profile)
        ai_profile_row.addWidget(self._edit_ai_profile)
        self._delete_ai_profile = QPushButton("Delete AI Profile")
        self._delete_ai_profile.setObjectName("DeleteAiProfileButton")
        self._delete_ai_profile.setAccessibleName("Delete the selected AI profile")
        self._delete_ai_profile.setEnabled(False)
        self._delete_ai_profile.clicked.connect(self._on_delete_ai_profile)
        ai_profile_row.addWidget(self._delete_ai_profile)
        ai_profile_row.addWidget(self._create_ai_profile)
        layout.addLayout(ai_profile_row)

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
            self._selected_source_type = None
            self._selected_topic_name = None
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
                    self._selected_source_type = row.source_type
                    self._selected_topic_name = row.name
            if selected_row >= 0:
                self._table.selectRow(selected_row)
            can_act_on_gmail = (
                not state.busy
                and state.selected_id is not None
                and self._selected_source_type == "GMAIL"
            )
            self._retrieve.setEnabled(can_act_on_gmail)
            self._save.setEnabled(can_act_on_gmail)
            self._apply_ai_profile_combo(state)
        finally:
            self._updating = False

    def _apply_ai_profile_combo(self, state: TopicsViewState) -> None:
        combo = self._ai_profile_combo
        combo.clear()
        combo.addItem(_NOT_CONFIGURED_OPTION, None)
        selected_index = 0
        for index, option in enumerate(state.ai_profile_options, start=1):
            combo.addItem(option.name, option.id)
            if option.id == state.selected_ai_profile_id:
                selected_index = index
        combo.setCurrentIndex(selected_index)
        combo.setEnabled(not state.busy and state.selected_id is not None)
        self._selected_ai_profile_id = state.selected_ai_profile_id
        has_profile = not state.busy and state.selected_ai_profile_id is not None
        self._edit_ai_profile.setEnabled(has_profile)
        self._delete_ai_profile.setEnabled(has_profile)

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self._table.selectedItems()
        if not items:
            return
        topic_id = items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(topic_id, str):
            self.apply_state(self._vm.select(topic_id))

    def _on_ai_profile_selected(self, index: int) -> None:
        if self._updating or index < 0:
            return
        profile_id = self._ai_profile_combo.itemData(index)
        self.apply_state(self._vm.assign_ai_profile(profile_id))

    def _on_create_ai_profile(self) -> None:
        dialog = CreateAIProfileDialog(self, topic_name=self._selected_topic_name)
        if dialog.exec() != CreateAIProfileDialog.DialogCode.Accepted:
            return
        data = dialog.form_data()
        self.apply_state(
            self._vm.create_ai_profile(
                name=data.name,
                description=data.description or None,
                instructions=data.instructions,
                output_schema_version=data.output_schema_version,
                assign_to_selected_topic=data.assign_to_selected_topic,
                output_style=data.output_style,
            )
        )

    def _on_edit_ai_profile(self) -> None:
        profile_id = self._selected_ai_profile_id
        if profile_id is None:
            return
        existing = self._vm.get_ai_profile(profile_id)
        if existing is None:
            self.apply_state(self._vm.load())
            return
        dialog = CreateAIProfileDialog(self, existing=existing)
        if dialog.exec() != CreateAIProfileDialog.DialogCode.Accepted:
            return
        data = dialog.form_data()
        self.apply_state(
            self._vm.update_ai_profile(
                profile_id=profile_id,
                name=data.name,
                description=data.description or None,
                instructions=data.instructions,
                output_style=data.output_style,
            )
        )

    def _on_delete_ai_profile(self) -> None:
        profile_id = self._selected_ai_profile_id
        if profile_id is None:
            return
        profile_name = self._ai_profile_combo.currentText()
        answer = QMessageBox.question(
            self,
            "Delete AI Profile",
            f"Delete the AI profile '{profile_name}'?\n\n"
            "Every topic using it will have no AI profile until you assign "
            "one. Analyses it already produced are kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.apply_state(self._vm.delete_ai_profile(profile_id))

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

    def _on_retrieve(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self.apply_state(self._vm.set_busy(True))
        self._thread = QThread(self)
        self._worker = _RetrieveMessagesWorker(self._vm)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished_ok.connect(self._on_retrieve_ok)
        self._worker.finished_err.connect(self._on_retrieve_err)
        self._worker.finished_ok.connect(self._thread.quit)
        self._worker.finished_err.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_retrieve_ok(self, state: object) -> None:
        if isinstance(state, TopicsViewState):
            self._vm.set_busy(False)
            self.apply_state(state)

    def _on_retrieve_err(self, message: str) -> None:
        state = self._vm.set_busy(False)
        self.apply_state(
            TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                error_message=message,
            )
        )

    def _cleanup_thread(self) -> None:
        self._worker = None
        self._thread = None

    def _on_save(self) -> None:
        if self._save_thread is not None and self._save_thread.isRunning():
            return
        self.apply_state(self._vm.set_busy(True))
        self._save_thread = QThread(self)
        self._save_worker = _SaveMessagesWorker(self._vm)
        self._save_worker.moveToThread(self._save_thread)
        self._save_thread.started.connect(self._save_worker.run)
        self._save_worker.finished_ok.connect(self._on_save_ok)
        self._save_worker.finished_err.connect(self._on_save_err)
        self._save_worker.finished_ok.connect(self._save_thread.quit)
        self._save_worker.finished_err.connect(self._save_thread.quit)
        self._save_thread.finished.connect(self._cleanup_save_thread)
        self._save_thread.start()

    def _on_save_ok(self, state: object) -> None:
        if isinstance(state, TopicsViewState):
            self._vm.set_busy(False)
            self.apply_state(state)

    def _on_save_err(self, message: str) -> None:
        state = self._vm.set_busy(False)
        self.apply_state(
            TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                error_message=message,
            )
        )

    def _cleanup_save_thread(self) -> None:
        self._save_worker = None
        self._save_thread = None
