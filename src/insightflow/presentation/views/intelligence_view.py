"""Intelligence list and event details view."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
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

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Intelligence", refresh_slot=self.refresh)
        layout.addWidget(header)
        make_banners(layout)

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
                        row.topic_id,
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

    def _render_details(self, details: EventDetailsState | None) -> None:
        if details is None:
            self._details.setPlainText("Select an intelligence event to view details.")
            return
        lines = [
            f"Title: {details.title}",
            f"Topic: {details.topic_id}",
            f"Priority: {details.priority}",
            f"Status: {details.status}",
            f"Received: {details.received_at}",
            f"Source published: {details.source_published_at}",
            f"Source: {details.source_type} / {details.source_id}",
            f"External ID: {details.external_id}",
            "",
        ]
        if not details.ai_available:
            lines.append(details.ai_message or "AI analysis not available")
        else:
            key_facts = (
                [f"- {fact}" for fact in details.key_facts]
                if details.key_facts
                else ["- —"]
            )
            what_to_watch = (
                [f"- {item}" for item in details.what_to_watch]
                if details.what_to_watch
                else ["- —"]
            )
            lines.extend(
                [
                    "AI Summary:",
                    details.summary or "—",
                    "",
                    "Why it matters:",
                    details.why_it_matters or "—",
                    "",
                    "Key facts:",
                    *key_facts,
                    "",
                    "What to watch:",
                    *what_to_watch,
                    "",
                    "Market impact:",
                    details.market_impact or "—",
                ]
            )
        self._details.setPlainText("\n".join(lines))
