"""Dashboard UI tests."""

from __future__ import annotations

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.views.dashboard_view import DashboardView
from insightflow.presentation.windows.main_window import MainWindow


def test_dashboard_empty_and_populated(
    main_window: MainWindow, use_cases: ApplicationUseCases
) -> None:
    main_window.navigate_to("dashboard")
    dashboard = main_window._pages["dashboard"]
    assert isinstance(dashboard, DashboardView)
    dashboard.refresh()
    assert "Topics: 0" in dashboard._summary.text()
    assert "Monitoring: Not configured" in dashboard._summary.text()

    use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="evt-1",
            title="Headline",
            priority="HIGH",
        )
    )
    dashboard.refresh()
    assert "Recent events: 1" in dashboard._summary.text()
    assert "High priority: 1" in dashboard._summary.text()
    assert dashboard._events.rowCount() == 1
