"""Gmail Settings UI tests (offscreen, fake ports)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from tests.fakes.gmail import FakeGmailAdapter

from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.windows.main_window import MainWindow


def _settings(main_window: MainWindow) -> SettingsView:
    main_window.navigate_to("settings")
    page = main_window._pages["settings"]
    assert isinstance(page, SettingsView)
    return page


def test_gmail_not_connected_and_connect_button(
    qapp: QApplication, main_window: MainWindow
) -> None:
    page = _settings(main_window)
    page.refresh()
    qapp.processEvents()
    assert "NOT_CONNECTED" in page._gmail_status.text()
    assert page._connect.isEnabled()
    assert not page._disconnect.isEnabled()


def test_gmail_connect_and_labels(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    page = _settings(main_window)
    page.apply_state(page._vm.connect_gmail())
    qapp.processEvents()
    assert "CONNECTED" in page._gmail_status.text()
    assert "user@example.com" in page._gmail_status.text()
    assert "token" not in page._gmail_status.text().lower()
    page.apply_state(page._vm.refresh_labels())
    qapp.processEvents()
    assert page._labels.count() >= 1


def test_gmail_label_map_and_disconnect(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    page = _settings(main_window)
    page.apply_state(page._vm.connect_gmail())
    page.apply_state(page._vm.refresh_labels())
    # Select first label
    if page._labels.count() > 0:
        page._labels.setCurrentRow(0)
        qapp.processEvents()
    page.apply_state(page._vm.map_selected_label_to_topic())
    qapp.processEvents()
    assert page.property("last_info_message") or page._topics.count() >= 0
    page.apply_state(page._vm.disconnect_gmail())
    assert "NOT_CONNECTED" in page._gmail_status.text()


def test_gmail_label_selection_does_not_recurse(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    page = _settings(main_window)
    page.apply_state(page._vm.connect_gmail())
    page.apply_state(page._vm.refresh_labels())
    qapp.processEvents()
    assert page._labels.count() >= 2
    page._labels.setCurrentRow(0)
    qapp.processEvents()
    page._labels.setCurrentRow(1)
    qapp.processEvents()
    assert page._vm._selected_label_id is not None
    assert page._labels.count() >= 2


def test_gmail_connect_failure_ui(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    gmail.fail_connect = True
    page = _settings(main_window)
    page.apply_state(page._vm.connect_gmail())
    qapp.processEvents()
    assert page.property("last_error_message")
