"""Settings and diagnostics UI tests."""

from __future__ import annotations

from insightflow.presentation.views.diagnostics_view import DiagnosticsView
from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.windows.main_window import MainWindow

SECRET_MARKERS = (
    "token",
    "oauth",
    "password",
    "api_key",
    "secret_value",
    "Bearer ",
)


def test_settings_rendering(main_window: MainWindow) -> None:
    main_window.navigate_to("settings")
    page = main_window._pages["settings"]
    assert isinstance(page, SettingsView)
    page.refresh()
    assert page._table.rowCount() >= 5
    values = " ".join(
        page._table.item(row, 1).text()  # type: ignore[union-attr]
        for row in range(page._table.rowCount())
    ).lower()
    assert "insightflow" in values
    for marker in SECRET_MARKERS:
        assert marker not in values


def test_diagnostics_rendering_no_secrets(main_window: MainWindow) -> None:
    main_window.navigate_to("diagnostics")
    page = main_window._pages["diagnostics"]
    assert isinstance(page, DiagnosticsView)
    page.refresh()
    text = page.displayed_text().lower()
    assert "python" in text
    assert "not configured" in text or "not connected" in text
    for marker in SECRET_MARKERS:
        assert marker not in text
    # backend name is OK; secret material is not
    assert "memory" in text or "unavailable" in text or "windows" in text
