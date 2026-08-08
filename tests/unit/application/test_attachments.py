"""Attachment metadata use-case unit tests."""

from __future__ import annotations

import pytest
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.models import CreateIntelligenceEventRequest
from insightflow.application.exceptions import AttachmentNotFoundError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import Attachment, EventId


def test_get_and_list_attachments(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    event = use_cases.create_intelligence_event.execute(
        CreateIntelligenceEventRequest(
            source_type="GMAIL",
            source_id="acct-1",
            external_id="msg-att",
            title="With attachment",
        )
    )
    attachment = Attachment.create(
        event_id=EventId(event.id),
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=12,
    )
    with store.unit_of_work_factory() as uow:
        uow.attachments.add(attachment)
        uow.commit()

    loaded = use_cases.get_attachment.execute(attachment.id.value)
    assert loaded.filename == "report.pdf"
    listed = use_cases.list_event_attachments.execute(event.id)
    assert len(listed) == 1
    assert listed[0].id == attachment.id.value


def test_attachment_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(AttachmentNotFoundError):
        use_cases.get_attachment.execute("missing")
