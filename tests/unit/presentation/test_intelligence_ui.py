"""Intelligence UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.email import (
    EmailAddressDto,
    EmailAttachmentDto,
    EmailMessageDto,
    IngestTopicMessagesRequest,
)
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
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


def _make_email(
    message_id: str,
    *,
    label_id: str = "Label_2",
    subject: str = "Google Alert - trump iran",
    text_body: str | None = "Full alert body text.",
    attachments: tuple[EmailAttachmentDto, ...] = (),
) -> EmailMessageDto:
    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=message_id,
        thread_id=f"thread-{message_id}",
        subject=subject,
        sender=EmailAddressDto(email="alerts@google.com", display_name="Google Alerts"),
        recipients=(),
        cc=(),
        bcc=(),
        reply_to=(),
        message_id_header=None,
        in_reply_to=None,
        references=(),
        received_at=None,
        date_header=None,
        snippet="snippet",
        text_body=text_body,
        html_body=None,
        label_ids=(label_id,),
        attachments=attachments,
        size_estimate=100,
        history_id="1",
        content_truncated=False,
    )


def _ingest_one_message(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    *,
    label_id: str = "Label_2",
    topic_name: str = "TRUMP",
    message_id: str = "m1",
    attachments: tuple[EmailAttachmentDto, ...] = (),
    text_body: str | None = "Full alert body text.",
) -> str:
    """Connect, map a label to a topic, and persist one event. Returns topic_id."""
    use_cases.connect_gmail.execute()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id=label_id, topic_name=topic_name)
    )
    gmail.message_ids_by_label[label_id] = [message_id]
    gmail.messages_by_id = {
        message_id: _make_email(
            message_id, label_id=label_id, attachments=attachments, text_body=text_body
        )
    }
    use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=mapping.topic_id, max_messages=10)
    )
    return mapping.topic_id


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
    # No market impact assessment: the section is hidden, not shown as "—".
    assert "Market impact:" not in text


def test_clear_all_intelligence_events(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
) -> None:
    for external_id in ("clear-1", "clear-2"):
        use_cases.create_intelligence_event.execute(
            CreateIntelligenceEventRequest(
                source_type="GENERIC",
                source_id="local",
                external_id=external_id,
                title=f"Event {external_id}",
            )
        )
    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()
    assert page._table.rowCount() == 2
    assert page._clear_all.isEnabled() is True

    state = page._vm.clear_all()
    page.apply_state(state)
    qapp.processEvents()

    assert state.info_message is not None
    assert state.info_message.startswith("Cleared 2 intelligence event(s).")
    assert page._table.rowCount() == 0
    assert "Select an intelligence event" in page._details.toPlainText()
    assert page._clear_all.isEnabled() is False


def test_event_details_show_generated_content_for_custom_text(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    memory_store: InMemoryStore,
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="intel-custom",
            title="Google Alert - cm vijay",
        )
    )
    from insightflow.domain import AIOutputStyle, AIProfile

    profile = AIProfile.create(
        name="VIJAY",
        instructions="Write a Tamil script.",
        output_schema_version="v1",
        output_style=AIOutputStyle.CUSTOM_TEXT,
    )
    analysis = AIAnalysis.create(
        event_id=EventId(event.id),
        profile_id=profile.id,
        profile_version=1,
        provider="test",
        model="test-model",
        generated_content="தமிழ் செய்தி வரி",
    )
    analysis.mark_completed(summary="CM Vijay meets Naidu.")
    with memory_store.unit_of_work_factory() as uow:
        uow.profiles.add(profile)
        uow.analyses.add(analysis)
        uow.commit()

    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()
    text = page._details.toPlainText()
    assert "Generated content:\nதமிழ் செய்தி வரி" in text
    assert "CM Vijay meets Naidu." in text
    for hidden in ("Market impact:", "Key facts:", "What to watch:", "Sentiment:"):
        assert hidden not in text


def test_topic_name_displayed_instead_of_uuid(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
) -> None:
    topic_id = _ingest_one_message(use_cases, gmail, topic_name="TRUMP")

    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()

    assert page._table.rowCount() == 1
    topic_cell = page._table.item(0, 1)
    assert topic_cell is not None
    assert topic_cell.text() == "TRUMP"
    assert topic_id not in topic_cell.text()

    text = page._details.toPlainText()
    assert "Topic: TRUMP" in text
    assert topic_id not in text


def test_event_content_and_attachments_displayed(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
) -> None:
    attachments = (
        EmailAttachmentDto(
            filename="report.pdf",
            mime_type="application/pdf",
            attachment_id="A1",
            size_estimate=2048,
            is_inline=False,
        ),
    )
    _ingest_one_message(
        use_cases,
        gmail,
        text_body="Full alert body text.",
        attachments=attachments,
    )

    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()
    text = page._details.toPlainText()

    assert "Email content:" in text
    assert "Full alert body text." in text
    assert "Attachments:" in text
    assert "report.pdf" in text
    assert "application/pdf" in text
    assert "2048 bytes" in text


def test_empty_content_shows_placeholder(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
) -> None:
    use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GENERIC",
            source_id="local",
            external_id="intel-empty",
            title="No content event",
        )
    )
    page = _intelligence(main_window)
    page.refresh()
    qapp.processEvents()
    text = page._details.toPlainText()
    assert "No email content available." in text
    assert "Attachments:" not in text


def test_no_gmail_network_call_when_opening_event_details(
    qapp: QApplication,
    main_window: MainWindow,
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
) -> None:
    _ingest_one_message(use_cases, gmail)
    list_calls_before = gmail.list_calls
    get_calls_before = list(gmail.get_calls)

    page = _intelligence(main_window)
    state = page._vm.load()
    page.apply_state(state)
    qapp.processEvents()
    assert state.selected is not None
    page.apply_state(page._vm.select(state.selected.event_id))
    qapp.processEvents()

    assert gmail.list_calls == list_calls_before
    assert gmail.get_calls == get_calls_before
