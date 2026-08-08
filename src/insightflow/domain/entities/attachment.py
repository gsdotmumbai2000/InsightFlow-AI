"""Attachment entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from insightflow.domain.enums import (
    AttachmentDownloadStatus,
    AttachmentProcessingStatus,
)
from insightflow.domain.exceptions import DomainValidationError
from insightflow.domain.value_objects import AttachmentId, EventId, StorageReference
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class Attachment:
    """Metadata about an attachment associated with an intelligence event."""

    id: AttachmentId
    event_id: EventId
    filename: str
    content_type: str | None
    size_bytes: int | None
    storage_reference: StorageReference | None
    download_status: AttachmentDownloadStatus
    processing_status: AttachmentProcessingStatus
    created_at: datetime
    updated_at: datetime
    external_id: str | None = None

    def __post_init__(self) -> None:
        self.filename = require_non_empty(self.filename, "filename")
        if self.content_type is not None:
            self.content_type = require_non_empty(self.content_type, "content_type")
        if self.external_id is not None:
            self.external_id = require_non_empty(self.external_id, "external_id")
        if self.size_bytes is not None:
            if isinstance(self.size_bytes, bool) or not isinstance(
                self.size_bytes, int
            ):
                raise DomainValidationError("size_bytes must be an integer.")
            if self.size_bytes < 0:
                raise DomainValidationError("size_bytes cannot be negative.")
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        event_id: EventId,
        filename: str,
        content_type: str | None = None,
        size_bytes: int | None = None,
        external_id: str | None = None,
        storage_reference: StorageReference | None = None,
        attachment_id: AttachmentId | None = None,
        created_at: datetime | None = None,
    ) -> Attachment:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=attachment_id or AttachmentId.generate(),
            event_id=event_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_reference=storage_reference,
            download_status=AttachmentDownloadStatus.NOT_REQUESTED,
            processing_status=AttachmentProcessingStatus.NOT_REQUESTED,
            external_id=external_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
