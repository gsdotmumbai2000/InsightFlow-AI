"""SQLite attachment repository."""

from __future__ import annotations

import sqlite3

from insightflow.domain import Attachment, AttachmentId, EventId
from insightflow.infrastructure.database.errors import run_db
from insightflow.infrastructure.database.mappers import (
    attachment_from_row,
    attachment_to_row,
)


class SQLiteAttachmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, attachment: Attachment) -> None:
        def _op() -> None:
            row = attachment_to_row(attachment)
            self._connection.execute(
                """
                INSERT INTO attachments (
                    id, event_id, external_id, filename, mime_type, size_bytes,
                    download_status, processing_status, storage_reference,
                    content_hash, extracted_text, metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :event_id, :external_id, :filename, :mime_type, :size_bytes,
                    :download_status, :processing_status, :storage_reference,
                    NULL, NULL, NULL, :created_at, :updated_at
                )
                """,
                row,
            )

        run_db(_op, entity="attachment")

    def get(self, attachment_id: AttachmentId) -> Attachment | None:
        def _op() -> Attachment | None:
            row = self._connection.execute(
                "SELECT * FROM attachments WHERE id = ?",
                (attachment_id.value,),
            ).fetchone()
            return attachment_from_row(row) if row else None

        return run_db(_op, entity="attachment")

    def update(self, attachment: Attachment) -> None:
        def _op() -> None:
            row = attachment_to_row(attachment)
            cursor = self._connection.execute(
                """
                UPDATE attachments SET
                    filename = :filename,
                    mime_type = :mime_type,
                    size_bytes = :size_bytes,
                    download_status = :download_status,
                    processing_status = :processing_status,
                    storage_reference = :storage_reference,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                row,
            )
            if cursor.rowcount == 0:
                raise KeyError(attachment.id.value)

        run_db(_op, entity="attachment")

    def list_by_event(self, event_id: EventId) -> list[Attachment]:
        def _op() -> list[Attachment]:
            rows = self._connection.execute(
                """
                SELECT * FROM attachments
                WHERE event_id = ?
                ORDER BY created_at
                """,
                (event_id.value,),
            ).fetchall()
            return [attachment_from_row(row) for row in rows]

        return run_db(_op, entity="attachment")
