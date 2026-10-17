"""Topics page AI-profile assignment UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidget

from insightflow.application.dto.models import CreateAIProfileRequest
from insightflow.presentation.dialogs.create_ai_profile_dialog import (
    CreateAIProfileDialog,
)
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


def test_topics_page_shows_not_configured_when_no_profile(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    state = topics._vm.create_topic(name="TRUMP", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()

    assert _cell(topics._table, 0, 3) == "Not configured"
    assert topics._ai_profile_combo.currentText() == "Not configured"


def test_topics_page_shows_profile_name_when_assigned(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    state = topics._vm.create_topic(name="TRUMP", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()

    state = topics._vm.create_ai_profile(
        name="US Market Impact",
        description=None,
        instructions="Analyze US market-moving news.",
        output_schema_version="v1",
        assign_to_selected_topic=True,
    )
    topics.apply_state(state)
    qapp.processEvents()

    assert _cell(topics._table, 0, 3) == "US Market Impact"
    assert topics._ai_profile_combo.currentText() == "US Market Impact"


def test_creating_profile_without_assign_only_updates_option_list(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    state = topics._vm.create_topic(name="TRUMP", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()

    state = topics._vm.create_ai_profile(
        name="US Market Impact",
        description=None,
        instructions="Analyze US market-moving news.",
        output_schema_version="v1",
        assign_to_selected_topic=False,
    )
    topics.apply_state(state)
    qapp.processEvents()

    assert _cell(topics._table, 0, 3) == "Not configured"
    assert any(option.name == "US Market Impact" for option in state.ai_profile_options)
    assert topics._ai_profile_combo.count() == 2  # "Not configured" + the new profile


def test_assigning_profile_via_combo_updates_topic(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    state = topics._vm.create_topic(name="TRUMP", description=None, ai_profile_id=None)
    topics.apply_state(state)
    qapp.processEvents()

    profile_state = topics._vm.create_ai_profile(
        name="US Market Impact",
        description=None,
        instructions="Analyze US market-moving news.",
        output_schema_version="v1",
        assign_to_selected_topic=False,
    )
    topics.apply_state(profile_state)
    qapp.processEvents()

    profile_id = next(
        option.id
        for option in profile_state.ai_profile_options
        if option.name == "US Market Impact"
    )
    topics.apply_state(topics._vm.assign_ai_profile(profile_id))
    qapp.processEvents()

    assert _cell(topics._table, 0, 3) == "US Market Impact"
    topic = topics._vm._use_cases.get_topic.execute(state.selected_id or "")
    assert topic.ai_profile_id == profile_id


def test_edit_ai_profile_updates_instructions_and_name(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    topics.apply_state(
        topics._vm.create_topic(name="VIJAY", description=None, ai_profile_id=None)
    )
    qapp.processEvents()
    assert topics._edit_ai_profile.isEnabled() is False  # no profile yet

    state = topics._vm.create_ai_profile(
        name="VIJAY",
        description=None,
        instructions="Write a flash news script.",
        output_schema_version="v1",
        assign_to_selected_topic=True,
    )
    topics.apply_state(state)
    qapp.processEvents()
    assert topics._edit_ai_profile.isEnabled() is True

    profile_id = state.selected_ai_profile_id or ""
    state = topics._vm.update_ai_profile(
        profile_id=profile_id,
        name="VIJAY Tamil Shorts",
        description=None,
        instructions="Write a Tamil flash news script for YouTube Shorts.",
    )
    topics.apply_state(state)
    qapp.processEvents()

    assert state.error_message is None
    assert state.info_message == "Saved AI profile 'VIJAY Tamil Shorts' (version 2)."
    assert _cell(topics._table, 0, 3) == "VIJAY Tamil Shorts"
    profile = topics._vm.get_ai_profile(profile_id)
    assert profile is not None
    assert profile.instructions == "Write a Tamil flash news script for YouTube Shorts."


def test_edit_ai_profile_dialog_is_prefilled(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    created = topics._vm._use_cases.create_ai_profile.execute(
        CreateAIProfileRequest(
            name="US Market Impact",
            instructions="Analyze US market-moving news.",
            description="Markets",
        )
    )
    dialog = CreateAIProfileDialog(existing=created)
    data = dialog.form_data()
    assert dialog.windowTitle() == "Edit AI Profile"
    assert data.name == "US Market Impact"
    assert data.description == "Markets"
    assert data.instructions == "Analyze US market-moving news."
    assert dialog._output_schema_version.isReadOnly() is True
    assert data.assign_to_selected_topic is False
    dialog.close()


def test_delete_ai_profile_clears_topic_and_option_list(
    qapp: QApplication, main_window: MainWindow
) -> None:
    topics = _topics(main_window)
    topics.apply_state(
        topics._vm.create_topic(name="VIJAY", description=None, ai_profile_id=None)
    )
    qapp.processEvents()
    state = topics._vm.create_ai_profile(
        name="VIJAY",
        description=None,
        instructions="Write a Tamil script.",
        output_schema_version="v1",
        assign_to_selected_topic=True,
        output_style="CUSTOM_TEXT",
    )
    topics.apply_state(state)
    qapp.processEvents()
    assert topics._delete_ai_profile.isEnabled() is True

    state = topics._vm.delete_ai_profile(state.selected_ai_profile_id or "")
    topics.apply_state(state)
    qapp.processEvents()

    assert state.error_message is None
    assert state.info_message is not None
    assert state.info_message.startswith("Deleted AI profile 'VIJAY'")
    assert _cell(topics._table, 0, 3) == "Not configured"
    assert state.ai_profile_options == ()
    assert topics._delete_ai_profile.isEnabled() is False


def test_ai_profile_dialog_output_style() -> None:
    dialog = CreateAIProfileDialog()
    assert dialog.form_data().output_style == "ANALYSIS"
    dialog._output_style.setCurrentIndex(dialog._output_style.findData("CUSTOM_TEXT"))
    assert dialog.form_data().output_style == "CUSTOM_TEXT"
    dialog.close()


def test_create_ai_profile_dialog_fields() -> None:
    dialog = CreateAIProfileDialog(topic_name="TRUMP")
    dialog._name.setText("US Market Impact")
    dialog._description.setText("Market-moving news analysis")
    dialog._instructions.setPlainText("Analyze US market-moving news.")
    dialog._output_schema_version.setText("v1")
    data = dialog.form_data()
    assert data.name == "US Market Impact"
    assert data.description == "Market-moving news analysis"
    assert data.instructions == "Analyze US market-moving news."
    assert data.output_schema_version == "v1"
    assert data.assign_to_selected_topic is True
    dialog.close()


def test_create_ai_profile_dialog_defaults_output_schema_version() -> None:
    dialog = CreateAIProfileDialog()
    dialog._name.setText("Default")
    dialog._instructions.setPlainText("Instructions")
    data = dialog.form_data()
    assert data.output_schema_version == "v1"
    assert data.assign_to_selected_topic is False
    dialog.close()
