"""Settings page with Gmail connection, label mapping, and monitoring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
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


def _monitoring_status_line(status: str) -> str:
    """Human-readable status text — clarifies the non-obvious PAUSED case.

    PAUSED means: monitoring was previously started and left in a
    RUNNING/STARTING state, but this application process currently has no
    live worker for it (e.g. the app was closed or restarted without
    clicking "Stop Monitoring" first). It is deliberately distinct from
    STOPPED (the user explicitly stopped monitoring) — both mean "not
    currently running," but only PAUSED implies "click Start Monitoring
    to resume."
    """
    if status == "PAUSED":
        return "PAUSED (not running in this session — click Start Monitoring)"
    return status


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


class _MonitoringActionWorker(QObject):
    """Runs one monitoring view-model action off the GUI thread (Phase 10).

    Shared by Authorize/Revoke Pub/Sub, Start/Stop Monitoring, and Renew
    Watch — each has the identical shape (call a no-arg view-model method,
    receive a ``SettingsViewState`` back), so one worker parameterized by
    the action avoids five near-duplicate ``QObject`` subclasses.
    """

    finished_ok = Signal(object)
    finished_err = Signal(str)

    def __init__(self, action: Callable[[], SettingsViewState]) -> None:
        super().__init__()
        self._action = action

    def run(self) -> None:
        state = self._action()
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
        self._monitoring_thread: QThread | None = None
        self._monitoring_worker: _MonitoringActionWorker | None = None
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

        monitoring_title = QLabel("Real-time monitoring")
        monitoring_title.setObjectName("SectionTitle")
        layout.addWidget(monitoring_title)

        self._monitoring_status = QLabel()
        self._monitoring_status.setObjectName("MonitoringStatusLabel")
        self._monitoring_status.setAccessibleName("Monitoring status")
        self._monitoring_status.setWordWrap(True)
        layout.addWidget(self._monitoring_status)

        pubsub_actions = QHBoxLayout()
        self._authorize_pubsub = QPushButton("Authorize Pub/Sub")
        self._authorize_pubsub.setAccessibleName("Authorize Pub/Sub access")
        self._revoke_pubsub = QPushButton("Revoke Pub/Sub")
        self._revoke_pubsub.setAccessibleName("Revoke Pub/Sub access")
        self._authorize_pubsub.clicked.connect(self._on_connect_pubsub)
        self._revoke_pubsub.clicked.connect(self._on_disconnect_pubsub)
        pubsub_actions.addWidget(self._authorize_pubsub)
        pubsub_actions.addWidget(self._revoke_pubsub)
        pubsub_actions.addStretch(1)
        layout.addLayout(pubsub_actions)

        monitoring_actions = QHBoxLayout()
        self._start_monitoring = QPushButton("Start Monitoring")
        self._start_monitoring.setObjectName("PrimaryButton")
        self._start_monitoring.setAccessibleName("Start Monitoring")
        self._stop_monitoring = QPushButton("Stop Monitoring")
        self._stop_monitoring.setAccessibleName("Stop Monitoring")
        self._renew_watch = QPushButton("Renew Watch")
        self._renew_watch.setAccessibleName("Renew Gmail watch")
        self._start_monitoring.clicked.connect(self._on_start_monitoring)
        self._stop_monitoring.clicked.connect(self._on_stop_monitoring)
        self._renew_watch.clicked.connect(self._on_renew_watch)
        monitoring_actions.addWidget(self._start_monitoring)
        monitoring_actions.addWidget(self._stop_monitoring)
        monitoring_actions.addWidget(self._renew_watch)
        monitoring_actions.addStretch(1)
        layout.addLayout(monitoring_actions)

        ai_title = QLabel("AI analysis")
        ai_title.setObjectName("SectionTitle")
        layout.addWidget(ai_title)

        self._ai_analysis_enabled = QCheckBox(
            "Analyze new emails automatically (turn off to stop AI cost; "
            "the Analyze button still works)"
        )
        self._ai_analysis_enabled.setObjectName("AIAnalysisEnabledCheckbox")
        self._ai_analysis_enabled.setAccessibleName("Analyze new emails automatically")
        self._ai_analysis_enabled.toggled.connect(self._on_ai_analysis_toggled)
        layout.addWidget(self._ai_analysis_enabled)

        ai_row = QHBoxLayout()
        ai_row.addWidget(QLabel("Max output tokens:"))
        self._ai_output_tokens = QSpinBox()
        self._ai_output_tokens.setObjectName("AIOutputTokensInput")
        self._ai_output_tokens.setAccessibleName("AI max output tokens")
        self._ai_output_tokens.setSingleStep(256)
        self._ai_output_tokens.setMinimumWidth(120)
        ai_row.addWidget(self._ai_output_tokens)
        self._save_ai_output_tokens = QPushButton("Save")
        self._save_ai_output_tokens.setAccessibleName("Save AI max output tokens")
        self._save_ai_output_tokens.clicked.connect(self._on_save_ai_output_tokens)
        ai_row.addWidget(self._save_ai_output_tokens)
        self._reset_ai_output_tokens = QPushButton("Reset to default")
        self._reset_ai_output_tokens.setAccessibleName(
            "Reset AI max output tokens to default"
        )
        self._reset_ai_output_tokens.clicked.connect(self._on_reset_ai_output_tokens)
        ai_row.addWidget(self._reset_ai_output_tokens)
        ai_row.addStretch(1)
        layout.addLayout(ai_row)

        self._ai_output_tokens_hint = QLabel()
        self._ai_output_tokens_hint.setObjectName("MutedLabel")
        self._ai_output_tokens_hint.setWordWrap(True)
        layout.addWidget(self._ai_output_tokens_hint)

        startup_title = QLabel("Background Agent")
        startup_title.setObjectName("SectionTitle")
        layout.addWidget(startup_title)

        self._start_with_windows = QCheckBox("Start InsightFlow AI with Windows")
        self._start_with_windows.setObjectName("StartWithWindowsCheckbox")
        self._start_with_windows.setAccessibleName("Start InsightFlow AI with Windows")
        self._start_with_windows.toggled.connect(self._on_start_with_windows_toggled)
        layout.addWidget(self._start_with_windows)

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

            self._monitoring_status.setText(
                f"Status: {_monitoring_status_line(state.monitoring_status)}\n"
                f"Account: {state.monitoring_account_email}\n"
                f"Watched topics: {state.monitoring_watched_topics}\n"
                f"Pub/Sub: {state.monitoring_pubsub_project} / "
                f"{state.monitoring_pubsub_topic} / "
                f"{state.monitoring_pubsub_subscription}\n"
                f"Watch expiration: {state.monitoring_watch_expiration}\n"
                f"Last sync: {state.monitoring_last_sync}\n"
                f"Last notification: {state.monitoring_last_notification}\n"
                f"Last error: {state.monitoring_last_error}"
            )
            running = state.monitoring_status in ("STARTING", "RUNNING")
            self._authorize_pubsub.setEnabled(
                not state.busy and not state.pubsub_connected
            )
            self._revoke_pubsub.setEnabled(
                not state.busy and state.pubsub_connected and not running
            )
            self._start_monitoring.setEnabled(
                not state.busy and connected and state.pubsub_connected and not running
            )
            self._stop_monitoring.setEnabled(not state.busy and running)
            self._renew_watch.setEnabled(not state.busy and connected and running)

            self._start_with_windows.blockSignals(True)
            self._start_with_windows.setChecked(state.startup_registered)
            self._start_with_windows.blockSignals(False)
            self._start_with_windows.setEnabled(not state.busy)

            self._ai_analysis_enabled.blockSignals(True)
            self._ai_analysis_enabled.setChecked(state.ai_analysis_enabled is not False)
            self._ai_analysis_enabled.blockSignals(False)
            self._ai_analysis_enabled.setEnabled(
                not state.busy and state.ai_analysis_enabled is not None
            )

            limit = state.ai_output_tokens
            self._ai_output_tokens.setEnabled(not state.busy and limit is not None)
            self._save_ai_output_tokens.setEnabled(not state.busy and limit is not None)
            self._reset_ai_output_tokens.setEnabled(
                not state.busy and limit is not None and limit.overridden
            )
            if limit is None:
                self._ai_output_tokens_hint.setText("AI settings are unavailable.")
            else:
                self._ai_output_tokens.setRange(limit.minimum, limit.maximum)
                self._ai_output_tokens.setValue(limit.effective)
                source = (
                    "set here"
                    if limit.overridden
                    else "default from INSIGHTFLOW_AI_MAX_OUTPUT_TOKENS"
                )
                self._ai_output_tokens_hint.setText(
                    f"Currently {limit.effective} ({source}; default "
                    f"{limit.configured_default}). The longest reply the AI may "
                    "write; raise it if analyses fail with 'cut off at the "
                    "output token limit' — Tamil and other non-English text "
                    "uses more tokens. Applies to the next analysis, no restart."
                )

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

    # -- Real-time monitoring actions (Phase 10) -------------------------

    def _run_monitoring_action(self, action: Callable[[], SettingsViewState]) -> None:
        if self._monitoring_thread is not None and self._monitoring_thread.isRunning():
            return
        self.apply_state(self._vm.set_busy(True))
        self._monitoring_thread = QThread(self)
        self._monitoring_worker = _MonitoringActionWorker(action)
        self._monitoring_worker.moveToThread(self._monitoring_thread)
        self._monitoring_thread.started.connect(self._monitoring_worker.run)
        self._monitoring_worker.finished_ok.connect(self._on_monitoring_ok)
        self._monitoring_worker.finished_err.connect(self._on_monitoring_err)
        self._monitoring_worker.finished_ok.connect(self._monitoring_thread.quit)
        self._monitoring_worker.finished_err.connect(self._monitoring_thread.quit)
        self._monitoring_thread.finished.connect(self._cleanup_monitoring_thread)
        self._monitoring_thread.start()

    def _on_monitoring_ok(self, state: object) -> None:
        if isinstance(state, SettingsViewState):
            self._vm.set_busy(False)
            self.apply_state(state)

    def _on_monitoring_err(self, message: str) -> None:
        state = self._vm.set_busy(False)
        self.apply_state(replace(state, error_message=message))

    def _cleanup_monitoring_thread(self) -> None:
        self._monitoring_worker = None
        self._monitoring_thread = None

    def _on_connect_pubsub(self) -> None:
        self._run_monitoring_action(self._vm.connect_pubsub)

    def _on_disconnect_pubsub(self) -> None:
        self._run_monitoring_action(self._vm.disconnect_pubsub)

    def _on_start_monitoring(self) -> None:
        self._run_monitoring_action(self._vm.start_monitoring)

    def _on_stop_monitoring(self) -> None:
        self._run_monitoring_action(self._vm.stop_monitoring)

    def _on_renew_watch(self) -> None:
        self._run_monitoring_action(self._vm.renew_watch)

    # -- Windows auto-start (Phase 13) ------------------------------------

    def _on_ai_analysis_toggled(self, checked: bool) -> None:
        if self._applying_state:
            return
        self.apply_state(self._vm.set_ai_analysis_enabled(checked))

    def _on_save_ai_output_tokens(self) -> None:
        self.apply_state(
            self._vm.set_ai_output_token_limit(self._ai_output_tokens.value())
        )

    def _on_reset_ai_output_tokens(self) -> None:
        self.apply_state(self._vm.set_ai_output_token_limit(None))

    def _on_start_with_windows_toggled(self, checked: bool) -> None:
        if self._applying_state:
            return
        action = self._vm.enable_startup if checked else self._vm.disable_startup
        self._run_monitoring_action(action)
