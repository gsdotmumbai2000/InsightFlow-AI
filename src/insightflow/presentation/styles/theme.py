"""Centralized Qt stylesheet for Phase 6."""

from __future__ import annotations

# Professional light desktop theme — colors live here, not in widgets.
APPLICATION_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #1f2933;
}
QMainWindow, QDialog {
    background: #f4f6f8;
}
/* Content lists (Settings labels/topics, etc.) — light surface for readable text */
QListWidget {
    background: #ffffff;
    color: #1f2933;
    border: 1px solid #cbd2d9;
    border-radius: 4px;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    padding: 6px 10px;
    color: #1f2933;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #bfdbfe;
    color: #0f172a;
}
QListWidget::item:hover:!selected {
    background: #eef2f6;
}
QListWidget#NavList {
    background: #1f2a37;
    color: #e5e7eb;
    border: none;
    padding: 8px 0;
    outline: none;
}
QListWidget#NavList::item {
    padding: 10px 16px;
    margin: 2px 8px;
    border-radius: 6px;
    color: #e5e7eb;
}
QListWidget#NavList::item:selected {
    background: #334155;
    color: #ffffff;
}
QListWidget#NavList::item:hover {
    background: #2b3645;
}
QListWidget#NavList::item:hover:!selected {
    background: #2b3645;
}
QLabel#AppTitle {
    font-size: 18px;
    font-weight: 600;
    color: #0f172a;
    padding: 4px 0;
}
QLabel#PageTitle {
    font-size: 20px;
    font-weight: 600;
    color: #0f172a;
}
QLabel#SectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
    margin-top: 8px;
}
QLabel#MutedLabel, QLabel#EmptyState {
    color: #64748b;
}
QFrame#ContentCard {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
}
QTableWidget, QTextEdit, QLineEdit, QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #cbd2d9;
    border-radius: 4px;
    selection-background-color: #bfdbfe;
}
QHeaderView::section {
    background: #eef2f6;
    padding: 6px;
    border: none;
    border-right: 1px solid #d9e2ec;
    font-weight: 600;
}
QPushButton {
    background: #e8eef5;
    border: 1px solid #9fb3c8;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background: #d9e6f5;
}
QPushButton:pressed {
    background: #c5d7ec;
}
QPushButton#PrimaryButton {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
}
QPushButton#PrimaryButton:hover {
    background: #1d4ed8;
}
QStatusBar {
    background: #eef2f6;
    border-top: 1px solid #d9e2ec;
}
QStatusBar::item {
    border: none;
}
QSplitter::handle {
    background: #d9e2ec;
}
"""


def apply_application_theme(app: object) -> None:
    """Apply the centralized stylesheet to a QApplication."""
    set_style = getattr(app, "setStyleSheet", None)
    if callable(set_style):
        set_style(APPLICATION_STYLESHEET)
