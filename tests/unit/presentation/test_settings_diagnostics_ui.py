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


def test_settings_ai_output_token_limit_save_and_reset(
    main_window: MainWindow,
) -> None:
    main_window.navigate_to("settings")
    page = main_window._pages["settings"]
    assert isinstance(page, SettingsView)
    page.refresh()
    default = page._ai_output_tokens.value()
    assert page._reset_ai_output_tokens.isEnabled() is False

    page._ai_output_tokens.setValue(4096)
    page._on_save_ai_output_tokens()

    assert page._ai_output_tokens.value() == 4096
    assert page._reset_ai_output_tokens.isEnabled() is True
    assert "4096" in page._ai_output_tokens_hint.text()

    page._on_reset_ai_output_tokens()

    assert page._ai_output_tokens.value() == default
    assert page._reset_ai_output_tokens.isEnabled() is False


def test_settings_ai_analysis_switch(main_window: MainWindow) -> None:
    main_window.navigate_to("settings")
    page = main_window._pages["settings"]
    assert isinstance(page, SettingsView)
    page.refresh()
    assert page._ai_analysis_enabled.isChecked() is True

    page._ai_analysis_enabled.setChecked(False)  # fires the toggle handler

    assert page._ai_analysis_enabled.isChecked() is False
    assert page._vm._use_cases.get_ai_analysis_enabled.execute() is False

    page._ai_analysis_enabled.setChecked(True)

    assert page._vm._use_cases.get_ai_analysis_enabled.execute() is True


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
