"""Attachment metadata use cases (no filesystem access)."""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope, use_case_scope
from insightflow.application.dto.mappers import attachment_to_dto
from insightflow.application.dto.models import AttachmentDto
from insightflow.application.exceptions import (
    AttachmentNotFoundError,
    EventNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import AttachmentId, EventId


class GetAttachmentUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, attachment_id: str) -> AttachmentDto:
        with (
            use_case_scope("GetAttachment"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            attachment = uow.attachments.get(AttachmentId(attachment_id))
            if attachment is None:
                raise AttachmentNotFoundError(f"Attachment not found: {attachment_id}")
            return attachment_to_dto(attachment)


class ListEventAttachmentsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, event_id: str) -> list[AttachmentDto]:
        with (
            use_case_scope("ListEventAttachments"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            if uow.events.get(EventId(event_id)) is None:
                raise EventNotFoundError(f"Event not found: {event_id}")
            items = uow.attachments.list_by_event(EventId(event_id))
            return [attachment_to_dto(item) for item in items]
