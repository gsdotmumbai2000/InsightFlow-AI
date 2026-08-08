"""Main window and navigation UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from insightflow.presentation.windows.main_window import NAV_PAGES, MainWindow


def test_main_window_construction(main_window: MainWindow) -> None:
    assert main_window.windowTitle() == "InsightFlow AI"
    assert main_window.minimumWidth() >= 1024
    assert main_window.statusBar() is not None
    assert main_window._status_app.text() == "Application: Running"
    assert main_window._status_gmail.text() == "Gmail: Not connected"
    assert main_window._status_ai.text() == "AI: Not configured"
    assert main_window._status_db.text() == "Database: Ready"


def test_navigation_switches_pages(qapp: QApplication, main_window: MainWindow) -> None:
    assert main_window.current_page_key() == "dashboard"
    for _label, key in NAV_PAGES:
        main_window.navigate_to(key)
        qapp.processEvents()
        assert main_window.current_page_key() == key
        assert main_window._stack.currentIndex() == [k for _, k in NAV_PAGES].index(key)
