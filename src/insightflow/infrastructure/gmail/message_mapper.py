"""Map a raw Gmail ``messages.get`` response into ``EmailMessageDto``."""

from __future__ import annotations

from typing import Any

from insightflow.application.dto.email import EmailMessageDto
from insightflow.infrastructure.gmail.mime import (
    DEFAULT_MAX_BODY_BYTES,
    extract_content,
    headers_map,
    parse_addresses,
    parse_date_header,
    parse_internal_date,
)


def _split_references(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(token for token in value.split() if token)


def map_gmail_message_to_dto(
    raw: dict[str, Any],
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> EmailMessageDto:
    """Normalize a raw Gmail message resource (format=FULL) into a DTO."""
    payload = raw.get("payload") or {}
    headers = headers_map(payload)
    extracted = extract_content(payload, max_body_bytes=max_body_bytes)

    senders = parse_addresses(headers.get("from"))
    label_ids = tuple(str(label) for label in (raw.get("labelIds") or []))

    subject = headers.get("subject")

    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=str(raw.get("id") or ""),
        thread_id=raw.get("threadId"),
        subject=subject.strip() if subject else None,
        sender=senders[0] if senders else None,
        recipients=parse_addresses(headers.get("to")),
        cc=parse_addresses(headers.get("cc")),
        bcc=parse_addresses(headers.get("bcc")),
        reply_to=parse_addresses(headers.get("reply-to")),
        message_id_header=headers.get("message-id"),
        in_reply_to=headers.get("in-reply-to"),
        references=_split_references(headers.get("references")),
        received_at=parse_internal_date(raw.get("internalDate")),
        date_header=parse_date_header(headers.get("date")),
        snippet=raw.get("snippet"),
        text_body=extracted.text_body,
        html_body=extracted.html_body,
        label_ids=label_ids,
        attachments=extracted.attachments,
        size_estimate=raw.get("sizeEstimate"),
        history_id=raw.get("historyId"),
        content_truncated=extracted.content_truncated,
    )
