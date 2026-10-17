"""Presentation composition helpers for the GUI shell."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.models.context import PresentationContext
from insightflow.presentation.monitoring_bridge import MonitoringRefreshBridge
from insightflow.presentation.refresh import PresentationRefreshHub
from insightflow.presentation.styles.theme import apply_application_theme
from insightflow.presentation.viewmodels.dashboard_view_model import DashboardViewModel
from insightflow.presentation.viewmodels.diagnostics_view_model import (
    DiagnosticsViewModel,
)
from insightflow.presentation.viewmodels.intelligence_view_model import (
    IntelligenceViewModel,
)
from insightflow.presentation.viewmodels.notifications_view_model import (
    NotificationsViewModel,
)
from insightflow.presentation.viewmodels.settings_view_model import SettingsViewModel
from insightflow.presentation.viewmodels.topics_view_model import TopicsViewModel
from insightflow.presentation.views.dashboard_view import DashboardView
from insightflow.presentation.views.diagnostics_view import DiagnosticsView
from insightflow.presentation.views.intelligence_view import IntelligenceView
from insightflow.presentation.views.notifications_view import NotificationsView
from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.views.topics_view import TopicsView
from insightflow.presentation.windows.main_window import MainWindow


def create_qapplication(argv: list[str] | None = None) -> QApplication:
    """Create or reuse the process-wide QApplication."""
    existing = QApplication.instance()
    if existing is not None:
        return existing  # type: ignore[return-value]
    app = QApplication(argv if argv is not None else sys.argv)
    apply_application_theme(app)
    return app


def build_main_window(
    context: PresentationContext,
    *,
    executor: UiExecutor | None = None,
    refresh_hub: PresentationRefreshHub | None = None,
    on_close: Callable[[], None] | None = None,
) -> MainWindow:
    """Assemble MainWindow with explicit ViewModel dependencies."""
    ui_executor = executor or UiExecutor()
    hub = refresh_hub or PresentationRefreshHub()
    cases = context.use_cases

    window = MainWindow(
        app_name=context.app_name,
        dashboard=DashboardView(
            DashboardViewModel(cases, app_name=context.app_name, executor=ui_executor)
        ),
        intelligence=IntelligenceView(
            IntelligenceViewModel(cases, executor=ui_executor)
        ),
        topics=TopicsView(TopicsViewModel(cases, executor=ui_executor)),
        notifications=NotificationsView(
            NotificationsViewModel(cases, executor=ui_executor)
        ),
        settings=SettingsView(
            SettingsViewModel(
                use_cases=cases,
                config=context.config,
                directories=context.directories,
                database_path=context.database_path,
                diagnostics=context.diagnostics,
                executor=ui_executor,
            )
        ),
        diagnostics=DiagnosticsView(
            DiagnosticsViewModel(
                use_cases=cases,
                diagnostics=context.diagnostics,
                database_path=context.database_path,
                executor=ui_executor,
            )
        ),
        use_cases=cases,
        refresh_hub=hub,
        on_close=on_close,
    )

    # Background monitoring (GmailMonitoringWorker, a plain threading.Thread
    # — see application/services/monitoring_events.py) cannot import PySide6
    # to ask the UI to refresh. This bridge is the one place its
    # application-level notifications cross into Qt, marshaled onto the GUI
    # thread via a queued signal connection — never direct widget access
    # from the worker thread.
    monitoring_bridge = MonitoringRefreshBridge(hub, parent=window)
    cases.monitoring_event_broadcaster.set_listener(monitoring_bridge.notify)

    return window


def run_gui(
    context: PresentationContext,
    *,
    argv: list[str] | None = None,
    on_close: Callable[[], None] | None = None,
) -> int:
    """Start the Qt event loop with the main window."""
    qt_app = create_qapplication(argv)
    window = build_main_window(context, on_close=on_close)
    window.show()

    if os.environ.get("INSIGHTFLOW_UI_AUTO_QUIT", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        QTimer.singleShot(0, qt_app.quit)

    return int(qt_app.exec())
