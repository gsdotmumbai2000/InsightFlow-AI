"""Shared fixtures for presentation/UI tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import GmailLabelDto
from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.bootstrap.dependencies import build_container
from insightflow.configuration.env import MappingEnvironment
from insightflow.presentation.app import build_main_window, create_qapplication
from insightflow.presentation.models.context import PresentationContext
from insightflow.presentation.windows.main_window import MainWindow

_QAPP: QApplication | None = None


@pytest.fixture
def qapp() -> QApplication:
    """Process-wide QApplication for offscreen UI tests (never destroyed)."""
    global _QAPP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if _QAPP is None:
        _QAPP = create_qapplication(["insightflow-test"])
    return _QAPP


@pytest.fixture
def memory_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def gmail() -> FakeGmailAdapter:
    return FakeGmailAdapter(
        labels=[
            GmailLabelDto(label_id="Label_1", name="INBOX", label_type="system"),
            GmailLabelDto(label_id="Label_2", name="TRUMP", label_type="user"),
        ]
    )


@pytest.fixture
def use_cases(
    memory_store: InMemoryStore, gmail: FakeGmailAdapter
) -> ApplicationUseCases:
    return build_use_cases(
        memory_store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
    )


@pytest.fixture
def presentation_context(
    temp_environ: MappingEnvironment,
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
) -> PresentationContext:
    container = build_container(
        environ=temp_environ,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
    )
    return PresentationContext(
        app_name=container.app_name,
        version=container.version,
        config=container.config,
        directories=container.directories,
        diagnostics=container.diagnostics,
        database_path=container.database_path,
        use_cases=use_cases,
    )


@pytest.fixture
def main_window(
    qapp: QApplication, presentation_context: PresentationContext
) -> Iterator[MainWindow]:
    assert qapp is not None
    window = build_main_window(presentation_context)
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
    window.show()
    qapp.processEvents()
    yield window
    window.hide()
    window.close()
    qapp.processEvents()
