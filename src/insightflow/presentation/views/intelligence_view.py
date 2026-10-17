"""Intelligence list and event details view."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from insightflow.presentation.viewmodels.intelligence_view_model import (
    EventDetailsState,
    IntelligenceViewModel,
    IntelligenceViewState,
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


class IntelligenceView(QWidget):
    def __init__(
        self, view_model: IntelligenceViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.setObjectName("IntelligenceView")
        self.setAccessibleName("Intelligence page")
        self._updating = False
        self._selected_event_id: str | None = None

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Intelligence", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

        actions = QHBoxLayout()
        self._clear_all = QPushButton("Clear all")
        self._clear_all.setObjectName("ClearAllEventsButton")
        self._clear_all.setAccessibleName("Clear all intelligence events")
        self._clear_all.clicked.connect(self._on_clear_all_clicked)
        actions.addWidget(self._clear_all)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._empty = QLabel()
        self._empty.setObjectName("EmptyState")
        layout.addWidget(self._empty)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._table = QTableWidget(0, 5)
        self._table.setObjectName("IntelligenceEventsTable")
        self._table.setHorizontalHeaderLabels(
            ["Priority", "Topic", "Title", "Received", "Status"]
        )
        configure_table(self._table)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._table)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_title = QLabel("Event details")
        detail_title.setObjectName("SectionTitle")
        detail_layout.addWidget(detail_title)
        self._analyze_button = QPushButton("Analyze")
        self._analyze_button.setObjectName("AnalyzeButton")
        self._analyze_button.clicked.connect(self._on_analyze_clicked)
        detail_layout.addWidget(self._analyze_button)
        self._details = QTextEdit()
        self._details.setObjectName("EventDetailsText")
        self._details.setReadOnly(True)
        self._details.setAccessibleName("Event details")
        detail_layout.addWidget(self._details)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

    def refresh(self) -> None:
        self.apply_state(self._vm.load())

    def apply_state(self, state: IntelligenceViewState) -> None:
        clear_banners(self)
        if state.error_message:
            show_error(self, state.error_message)
        if state.info_message:
            show_info(self, state.info_message)
        self._clear_all.setEnabled(bool(state.rows))
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
                        row.priority,
                        row.topic_name,
                        row.title,
                        row.received_at,
                        row.status,
                    ],
                    user_data=row.id,
                )
                if state.selected and row.id == state.selected.event_id:
                    selected_row = index
            if selected_row >= 0:
                self._table.selectRow(selected_row)
            self._render_details(state.selected)
        finally:
            self._updating = False

    def _on_selection_changed(self) -> None:
        if self._updating:
            return
        items = self._table.selectedItems()
        if not items:
            return
        event_id = items[0].data(Qt.ItemDataRole.UserRole)
        if not isinstance(event_id, str):
            return
        self.apply_state(self._vm.select(event_id))

    def _on_analyze_clicked(self) -> None:
        if self._selected_event_id is None:
            return
        self.apply_state(self._vm.reanalyze(self._selected_event_id))

    def _on_clear_all_clicked(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear all intelligence events",
            "Delete every intelligence event, with its AI analysis and "
            "notifications?\n\nYour Gmail is not changed. Cleared emails are "
            "remembered and will not be imported again. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.apply_state(self._vm.clear_all())

    def _render_details(self, details: EventDetailsState | None) -> None:
        self._selected_event_id = details.event_id if details else None
        self._analyze_button.setEnabled(details is not None and details.can_reanalyze)
        self._analyze_button.setText(
            "Re-analyze" if details and details.ai_available else "Analyze"
        )
        if details is None:
            self._details.setPlainText("Select an intelligence event to view details.")
            return
        lines = [
            f"Title: {details.title}",
            f"Topic: {details.topic_name}",
            f"Priority: {details.priority}",
            f"Status: {details.status}",
            f"Received: {details.received_at}",
            f"Source published: {details.source_published_at}",
            f"Source: {details.source_type} / {details.source_id}",
            f"External ID: {details.external_id}",
        ]
        if details.thread_id and details.thread_id != "—":
            lines.append(f"Thread ID: {details.thread_id}")
        lines.extend(["", "Email content:", details.content])
        if details.attachments:
            lines.extend(["", "Attachments:"])
            lines.extend(f"- {item}" for item in details.attachments)
        lines.extend(["", f"AI status: {details.ai_status_label}"])
        if details.ai_available:
            lines.extend(_ai_sections(details))
        self._details.setPlainText("\n".join(lines))


def _ai_sections(details: EventDetailsState) -> list[str]:
    """AI result lines; a section the AI left empty is omitted entirely."""
    lines: list[str] = []

    def section(title: str, body: list[str]) -> None:
        if body:
            lines.extend(["", title, *body])

    section(
        "Generated content:",
        [details.generated_content] if details.generated_content else [],
    )
    section("AI Summary:", [details.summary] if details.summary else [])
    section(
        "Why it matters:", [details.why_it_matters] if details.why_it_matters else []
    )
    section("Key facts:", [f"- {fact}" for fact in details.key_facts])
    section("What to watch:", [f"- {item}" for item in details.what_to_watch])
    section("Market impact:", [details.market_impact] if details.market_impact else [])
    footer = [
        f"{label}: {value}"
        for label, value in (
            ("Sentiment", details.sentiment),
            ("Confidence", details.confidence),
            ("Entities", ", ".join(details.entities)),
        )
        if value and value != "—"
    ]
    if footer:
        lines.extend(["", *footer])
    return lines
