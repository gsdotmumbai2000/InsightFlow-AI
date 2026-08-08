"""Intelligence UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import AIAnalysis, EventId
from insightflow.presentation.views.intelligence_view import IntelligenceView
from insightflow.presentation.windows.main_window import MainWindow


def _intelligence(main_window: MainWindow) -> IntelligenceView:
    main_window.navigate_to("intelligence")
    page = main_window._pages["intelligence"]
    assert isinstance(page, IntelligenceView)
    return page


def test_event_list_selection_and_ai_unavailable(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
) -> None:
    page = _intelligence(main_window)
    page.refresh()
    assert "No intelligence events" in page._empty.text()
    assert "Select an intelligence event" in page._details.toPlainText()

    use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="intel-1",
            title="Breaking",
            priority="MEDIUM",
        )
    )
    page.refresh()
    qapp.processEvents()
    assert page._table.rowCount() == 1
    assert "Breaking" in page._details.toPlainText()
    assert "AI analysis not available" in page._details.toPlainText()


def test_event_details_with_analysis(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    memory_store: InMemoryStore,
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="intel-2",
            title="Analyzed",
            priority="HIGH",
        )
    )
    from insightflow.domain import AIProfile

    profile = AIProfile.create(
        name="Default",
        instructions="Summarize",
        output_schema_version="v1",
    )
    analysis = AIAnalysis.create(
        event_id=EventId(event.id),
        profile_id=profile.id,
        profile_version=1,
        provider="test",
        model="test-model",
    )
    analysis.mark_completed(
        summary="Concise summary",
    )
    analysis.why_it_matters = "Because markets care"
    analysis.key_facts = ("Fact A",)
    analysis.what_to_watch = ("Signal B",)
    with memory_store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.analyses.add(analysis)
        uow.commit()

    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()
    text = page._details.toPlainText()
    assert "Concise summary" in text
    assert "Because markets care" in text
    assert "Fact A" in text
    assert "Signal B" in text
