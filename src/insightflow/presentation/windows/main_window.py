"""Main application window with sidebar navigation and status bar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.refresh import PresentationRefreshHub
from insightflow.presentation.views.dashboard_view import DashboardView
from insightflow.presentation.views.diagnostics_view import DiagnosticsView
from insightflow.presentation.views.intelligence_view import IntelligenceView
from insightflow.presentation.views.notifications_view import NotificationsView
from insightflow.presentation.views.settings_view import SettingsView
from insightflow.presentation.views.topics_view import TopicsView

NAV_PAGES = (
    ("Dashboard", "dashboard"),
    ("Intelligence", "intelligence"),
    ("Topics", "topics"),
    ("Notifications", "notifications"),
    ("Settings", "settings"),
    ("Diagnostics", "diagnostics"),
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        app_name: str,
        dashboard: DashboardView,
        intelligence: IntelligenceView,
        topics: TopicsView,
        notifications: NotificationsView,
        settings: SettingsView,
        diagnostics: DiagnosticsView,
        use_cases: ApplicationUseCases | None = None,
        refresh_hub: PresentationRefreshHub | None = None,
        on_close: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_close = on_close
        self._use_cases = use_cases
        self._refresh_hub = refresh_hub or PresentationRefreshHub()
        self.setWindowTitle(app_name)
        self.setObjectName("MainWindow")
        self.setMinimumSize(1024, 640)
        self.resize(1280, 800)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(app_name)
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #f8fafc; background: #1f2a37; padding: 16px;")
        sidebar_layout.addWidget(title)

        self._nav = QListWidget()
        self._nav.setObjectName("NavList")
        self._nav.setAccessibleName("Main navigation")
        for label, key in NAV_PAGES:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._nav.addItem(item)
        self._nav.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self._nav, stretch=1)
        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        self._stack.setObjectName("MainStack")
        self._pages = {
            "dashboard": dashboard,
            "intelligence": intelligence,
            "topics": topics,
            "notifications": notifications,
            "settings": settings,
            "diagnostics": diagnostics,
        }
        for _label, key in NAV_PAGES:
            self._stack.addWidget(self._pages[key])
        content_layout.addWidget(self._stack)
        root_layout.addWidget(content, stretch=1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.setObjectName("MainStatusBar")
        self._status_app = QLabel("Application: Running")
        self._status_gmail = QLabel("Gmail: Not connected")
        self._status_ai = QLabel("AI: Not configured")
        self._status_db = QLabel("Database: Ready")
        for status_label in (
            self._status_app,
            self._status_gmail,
            self._status_ai,
            self._status_db,
        ):
            status.addPermanentWidget(status_label)
        self.setStatusBar(status)

        self._refresh_hub.subscribe(self._on_refresh_signal)
        self._nav.setCurrentRow(0)
        self.refresh_current_page()

    @property
    def refresh_hub(self) -> PresentationRefreshHub:
        return self._refresh_hub

    def navigate_to(self, page_key: str) -> None:
        for index in range(self._nav.count()):
            item = self._nav.item(index)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == page_key:
                self._nav.setCurrentRow(index)
                return

    def current_page_key(self) -> str:
        item = self._nav.currentItem()
        # Qt stubs type currentItem() as non-optional once a selection exists.
        return str(item.data(Qt.ItemDataRole.UserRole))

    def refresh_current_page(self) -> None:
        self._refresh_status_bar()
        page = self._pages[self.current_page_key()]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def _refresh_status_bar(self) -> None:
        if self._use_cases is None:
            return
        try:
            status = self._use_cases.get_gmail_connection_status.execute()
        except Exception:
            self._status_gmail.setText("Gmail: Unavailable")
        else:
            if status.status == "CONNECTED" and status.account is not None:
                self._status_gmail.setText(f"Gmail: Connected ({status.account.email})")
            elif status.status == "REAUTHENTICATION_REQUIRED":
                self._status_gmail.setText("Gmail: Re-authentication required")
            elif status.status == "CONNECTION_FAILED":
                self._status_gmail.setText("Gmail: Connection failed")
            else:
                self._status_gmail.setText("Gmail: Not connected")
        self._refresh_ai_status()

    def _refresh_ai_status(self) -> None:
        if self._use_cases is None:
            return
        # Reports configuration truth (identical in the Desktop process and
        # the Background Agent — see ProcessRole, Phase 13), not
        # `ai_worker_handle.is_running`: the Desktop process never owns an
        # AIWorker, so that handle is always empty here even when the
        # Agent's worker is genuinely running. Checking it would just lie.
        ai_settings = self._use_cases.ai_settings
        if ai_settings.enabled:
            self._status_ai.setText(f"AI: {ai_settings.provider} (enabled)")
        else:
            self._status_ai.setText("AI: Disabled")

    def _on_nav_changed(self, row: int) -> None:
        if row < 0:
            return
        self._stack.setCurrentIndex(row)
        self.refresh_current_page()

    def _on_refresh_signal(self, _reason: str) -> None:
        self.refresh_current_page()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._on_close is not None:
            self._on_close()
        super().closeEvent(event)
