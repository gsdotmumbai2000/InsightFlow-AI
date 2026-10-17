"""Topics UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidget
from tests.fakes.gmail import FakeGmailAdapter

from insightflow.application.dto.email import (
    EmailAddressDto,
    EmailMessageDto,
)
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.presentation.dialogs.create_topic_dialog import CreateTopicDialog
from insightflow.presentation.views.topics_view import TopicsView
from insightflow.presentation.windows.main_window import MainWindow


def _topics(main_window: MainWindow) -> TopicsView:
    main_window.navigate_to("topics")
    page = main_window._pages["topics"]
    assert isinstance(page, TopicsView)
    return page


def _cell(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    assert item is not None
    return item.text()


def _make_email(message_id: str, *, label_id: str = "Label_2") -> EmailMessageDto:
    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=message_id,
        thread_id=f"thread-{message_id}",
        subject="Alert",
        sender=EmailAddressDto(email="alerts@google.com"),
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
        text_body="body",
        html_body=None,
        label_ids=(label_id,),
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def test_create_enable_disable_pause_resume_refresh(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    topics.refresh()
    assert topics._table.rowCount() == 0
    assert "No topics" in topics._empty.text()

    state = topics._vm.create_topic(
        name="Markets",
        description="Watch markets",
        ai_profile_id=None,
    )
    topics.apply_state(state)
    qapp.processEvents()
    assert topics._table.rowCount() == 1
    assert _cell(topics._table, 0, 0) == "Markets"

    topics._table.selectRow(0)
    qapp.processEvents()
    topics.apply_state(topics._vm.disable())
    assert _cell(topics._table, 0, 2) == "DISABLED"

    topics.apply_state(topics._vm.enable())
    assert _cell(topics._table, 0, 2) == "ENABLED"

    topics.apply_state(topics._vm.pause())
    assert _cell(topics._table, 0, 2) == "PAUSED"

    topics.apply_state(topics._vm.resume())
    assert _cell(topics._table, 0, 2) == "ENABLED"

    topics.refresh()
    assert topics._table.rowCount() == 1


def test_create_topic_validation_error(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    state = topics._vm.create_topic(name="", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()
    assert topics.property("last_error_message")
    assert topics._table.rowCount() == 0


def test_retrieve_button_enabled_only_for_gmail_topics(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    topics = _topics(main_window)
    topics.refresh()

    state = topics._vm.create_topic(name="Manual", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()
    topics._table.selectRow(0)
    qapp.processEvents()
    assert not topics._retrieve.isEnabled()


def test_retrieve_recent_messages_summarizes_result(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    gmail.connect()
    gmail.message_ids_by_label["Label_2"] = ["m1", "m2"]
    gmail.messages_by_id = {mid: _make_email(mid) for mid in ["m1", "m2"]}

    topics = _topics(main_window)
    mapping = topics._vm._use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_2", topic_name="TRUMP")
    )
    topics.apply_state(topics._vm.select(mapping.topic_id))
    qapp.processEvents()
    assert topics._retrieve.isEnabled()

    topics.apply_state(topics._vm.retrieve_recent_messages())
    qapp.processEvents()
    assert topics.property("last_info_message")
    assert "2" in str(topics.property("last_info_message"))


def test_save_recent_messages_persists_events_and_summarizes(
    qapp: QApplication, main_window: MainWindow, gmail: FakeGmailAdapter
) -> None:
    gmail.connect()
    gmail.message_ids_by_label["Label_2"] = ["m1", "m2"]
    gmail.messages_by_id = {mid: _make_email(mid) for mid in ["m1", "m2"]}

    topics = _topics(main_window)
    mapping = topics._vm._use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_2", topic_name="TRUMP")
    )
    topics.apply_state(topics._vm.select(mapping.topic_id))
    qapp.processEvents()
    assert topics._save.isEnabled()

    topics.apply_state(topics._vm.save_recent_messages())
    qapp.processEvents()
    assert topics.property("last_info_message")
    assert "Saved 2 new event" in str(topics.property("last_info_message"))

    events = topics._vm._use_cases.list_events_by_topic.execute(mapping.topic_id)
    assert len(events) == 2

    # Re-running must not create duplicates.
    topics.apply_state(topics._vm.save_recent_messages())
    qapp.processEvents()
    assert "Saved 0 new event" in str(topics.property("last_info_message"))
    assert "2 already stored" in str(topics.property("last_info_message"))
    events_after = topics._vm._use_cases.list_events_by_topic.execute(mapping.topic_id)
    assert len(events_after) == 2


def test_create_topic_dialog_fields(qapp: QApplication) -> None:
    dialog = CreateTopicDialog()
    dialog._name.setText("Alpha")
    dialog._description.setPlainText("Desc")
    data = dialog.form_data()
    assert data.name == "Alpha"
    assert data.description == "Desc"
    dialog.close()
