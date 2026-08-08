"""Reusable helpers for table-based pages."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def make_page_header(
    title: str, *, refresh_slot: Callable[[], None]
) -> tuple[QWidget, QPushButton]:
    header = QWidget()
    layout = QHBoxLayout(header)
    layout.setContentsMargins(0, 0, 0, 0)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    refresh = QPushButton("Refresh")
    refresh.setObjectName("RefreshButton")
    refresh.setAccessibleName(f"Refresh {title}")
    refresh.clicked.connect(refresh_slot)
    layout.addWidget(title_label)
    layout.addStretch(1)
    layout.addWidget(refresh)
    return header, refresh


def configure_table(table: QTableWidget) -> None:
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSortingEnabled(False)
    table.horizontalHeader().setStretchLastSection(True)


def set_table_row(
    table: QTableWidget,
    row: int,
    values: list[str],
    *,
    user_data: str | None = None,
) -> None:
    for column, value in enumerate(values):
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if column == 0 and user_data is not None:
            item.setData(Qt.ItemDataRole.UserRole, user_data)
        table.setItem(row, column, item)


def show_error(parent: QWidget, message: str) -> None:
    parent.setProperty("last_error_message", message)
    banner = parent.findChild(QLabel, "ErrorBanner")
    if isinstance(banner, QLabel):
        banner.setText(message)
        banner.setVisible(True)


def show_info(parent: QWidget, message: str) -> None:
    parent.setProperty("last_info_message", message)
    banner = parent.findChild(QLabel, "InfoBanner")
    if isinstance(banner, QLabel):
        banner.setText(message)
        banner.setVisible(True)


def clear_banners(parent: QWidget) -> None:
    parent.setProperty("last_error_message", "")
    parent.setProperty("last_info_message", "")
    for name in ("ErrorBanner", "InfoBanner"):
        banner = parent.findChild(QLabel, name)
        if isinstance(banner, QLabel):
            banner.clear()
            banner.setVisible(False)


def make_banners(layout: QVBoxLayout) -> tuple[QLabel, QLabel]:
    error = QLabel()
    error.setObjectName("ErrorBanner")
    error.setWordWrap(True)
    error.setVisible(False)
    error.setStyleSheet("color: #b91c1c;")
    info = QLabel()
    info.setObjectName("InfoBanner")
    info.setWordWrap(True)
    info.setVisible(False)
    info.setStyleSheet("color: #166534;")
    layout.addWidget(error)
    layout.addWidget(info)
    return error, info


def vertical_page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    return page, layout
