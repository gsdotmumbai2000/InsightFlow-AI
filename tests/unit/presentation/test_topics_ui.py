"""Topics UI tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidget

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


def test_create_topic_dialog_fields(qapp: QApplication) -> None:
    dialog = CreateTopicDialog()
    dialog._name.setText("Alpha")
    dialog._description.setPlainText("Desc")
    data = dialog.form_data()
    assert data.name == "Alpha"
    assert data.description == "Desc"
    dialog.close()
