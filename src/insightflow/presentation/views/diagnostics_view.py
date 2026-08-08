"""Diagnostics page view."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QVBoxLayout, QWidget

from insightflow.presentation.viewmodels.diagnostics_view_model import (
    DiagnosticsViewModel,
)
from insightflow.presentation.widgets.page_helpers import (
    configure_table,
    make_page_header,
    set_table_row,
    vertical_page,
)


class DiagnosticsView(QWidget):
    def __init__(
        self, view_model: DiagnosticsViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.setObjectName("DiagnosticsView")
        self.setAccessibleName("Diagnostics page")

        page, layout = vertical_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        header, _ = make_page_header("Diagnostics", refresh_slot=self.refresh)
        layout.addWidget(header)

        note = QLabel("Runtime information for support. Secret values are never shown.")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._table = QTableWidget(0, 2)
        self._table.setObjectName("DiagnosticsTable")
        self._table.setHorizontalHeaderLabels(["Item", "Value"])
        configure_table(self._table)
        layout.addWidget(self._table, stretch=1)

    def refresh(self) -> None:
        state = self._vm.load()
        self._table.setRowCount(0)
        for index, (key, value) in enumerate(state.rows):
            self._table.insertRow(index)
            set_table_row(self._table, index, [key, value])

    def displayed_text(self) -> str:
        """Return concatenated table text for tests."""
        chunks: list[str] = []
        for row in range(self._table.rowCount()):
            for column in range(self._table.columnCount()):
                item = self._table.item(row, column)
                if item is not None:
                    chunks.append(item.text())
        return "\n".join(chunks)
