"""Recursive Gmail MIME payload parsing (Phase 8).

Gmail's ``messages.get`` (format=FULL) response already parses the raw
RFC 5322 message into a JSON tree (``payload`` with nested ``parts``); this
module walks that tree rather than re-parsing raw bytes. Address, date and
encoded-word header decoding reuse Python's standard :mod:`email` facilities
per project policy (no custom RFC 5322 parser).

Malformed/partial input must never raise past this module for content that
can be reasonably skipped; only truly unexpected structures propagate so the
adapter can translate them into ``GmailMessageParsingError``.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from insightflow.application.dto.email import EmailAddressDto, EmailAttachmentDto

GmailPayload = dict[str, Any]

# Google documents no hard per-message size cap for a single API response,
# but an unbounded email body must not be held in memory indefinitely.
# 2 MB comfortably covers legitimate Google Alert / newsletter bodies.
DEFAULT_MAX_BODY_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ExtractedContent:
    """Result of walking a Gmail message payload's MIME tree."""

    text_body: str | None
    html_body: str | None
    attachments: tuple[EmailAttachmentDto, ...]
    content_truncated: bool


def headers_map(part: GmailPayload) -> dict[str, str]:
    """Case-insensitive header lookup for one MIME part or the top payload."""
    result: dict[str, str] = {}
    for header in part.get("headers") or []:
        name = header.get("name")
        if not name:
            continue
        result[str(name).strip().lower()] = str(header.get("value") or "")
    return result


def decode_base64url(data: str) -> bytes:
    """Decode Gmail's base64url body data, tolerating missing padding."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def decode_mime_words(value: str) -> str:
    """Decode RFC 2047 encoded-words in a header value (e.g. subjects)."""
    if not value:
        return value
    try:
        decoded_parts = decode_header(value)
    except (ValueError, UnicodeError):
        return value
    pieces: list[str] = []
    for text, encoding in decoded_parts:
        if isinstance(text, bytes):
            charset = encoding or "utf-8"
            try:
                pieces.append(text.decode(charset, errors="replace"))
            except (LookupError, ValueError):
                pieces.append(text.decode("utf-8", errors="replace"))
        else:
            pieces.append(text)
    return "".join(pieces)


def parse_addresses(header_value: str | None) -> tuple[EmailAddressDto, ...]:
    """Parse a From/To/Cc/Bcc/Reply-To header into address DTOs."""
    if not header_value:
        return ()
    pairs = getaddresses([header_value])
    result: list[EmailAddressDto] = []
    for raw_name, address in pairs:
        address = address.strip()
        if not address:
            continue
        display_name = decode_mime_words(raw_name).strip() if raw_name else None
        result.append(EmailAddressDto(email=address, display_name=display_name or None))
    return tuple(result)


def parse_date_header(header_value: str | None) -> datetime | None:
    """Parse the original Date header; never raises on malformed input."""
    if not header_value:
        return None
    try:
        parsed = parsedate_to_datetime(header_value)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_internal_date(internal_date: str | None) -> datetime | None:
    """Convert Gmail's internalDate (epoch milliseconds) to aware UTC."""
    if not internal_date:
        return None
    try:
        millis = int(internal_date)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def _charset_of(headers: dict[str, str]) -> str:
    content_type = headers.get("content-type", "")
    probe = Message()
    try:
        probe["Content-Type"] = content_type
        return probe.get_content_charset() or "utf-8"
    except (ValueError, LookupError):
        return "utf-8"


def _decode_text_part(data_b64: str, headers: dict[str, str]) -> str:
    raw = decode_base64url(data_b64)
    charset = _charset_of(headers)
    try:
        return raw.decode(charset, errors="replace")
    except (LookupError, ValueError):
        return raw.decode("utf-8", errors="replace")


def _is_inline(part: GmailPayload, headers: dict[str, str]) -> bool:
    disposition = headers.get("content-disposition", "").lower()
    if "inline" in disposition:
        return True
    return bool(headers.get("content-id")) and "attachment" not in disposition


def sanitize_attachment_filename(filename: str) -> str:
    """Strip path components/control characters from an untrusted filename."""
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    return cleaned.strip() or "attachment"


def extract_content(
    payload: GmailPayload,
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> ExtractedContent:
    """Recursively walk a Gmail message payload's MIME tree.

    multipart/* parts are traversed; text/plain and text/html leaf parts
    (without a filename) become the body; parts with a filename or an
    attachment ID become attachment metadata (never downloaded here).
    """
    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[EmailAttachmentDto] = []
    truncated = False
    consumed = 0

    def _walk(part: Any) -> None:
        nonlocal truncated, consumed
        if not isinstance(part, dict):
            return
        mime_type = str(part.get("mimeType") or "")
        headers = headers_map(part)
        body = part.get("body") or {}
        sub_parts = part.get("parts") or []

        if mime_type.startswith("multipart/") or sub_parts:
            for sub in sub_parts:
                _walk(sub)
            return

        filename = str(part.get("filename") or "").strip()
        attachment_id = body.get("attachmentId")
        if filename or attachment_id:
            attachments.append(
                EmailAttachmentDto(
                    filename=sanitize_attachment_filename(filename or "attachment"),
                    mime_type=mime_type or "application/octet-stream",
                    attachment_id=attachment_id,
                    size_estimate=body.get("size"),
                    is_inline=_is_inline(part, headers),
                    content_id=headers.get("content-id"),
                )
            )
            return

        data = body.get("data")
        if not data or mime_type not in ("text/plain", "text/html"):
            return
        size = int(body.get("size") or 0)
        if consumed + size > max_body_bytes:
            truncated = True
            return
        consumed += size
        text = _decode_text_part(data, headers)
        if mime_type == "text/plain":
            text_parts.append(text)
        else:
            html_parts.append(text)

    _walk(payload)
    return ExtractedContent(
        text_body="\n".join(text_parts) if text_parts else None,
        html_body="\n".join(html_parts) if html_parts else None,
        attachments=tuple(attachments),
        content_truncated=truncated,
    )
