"""Gmail MIME parsing tests: fixtures for representative payload shapes.

These tests operate purely on Gmail's JSON payload tree (as returned by
``messages.get`` with ``format=FULL``) — no network, no real credentials.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from insightflow.application.dto.email import EmailAddressDto
from insightflow.infrastructure.gmail.message_mapper import map_gmail_message_to_dto
from insightflow.infrastructure.gmail.mime import (
    decode_mime_words,
    parse_date_header,
    parse_internal_date,
    sanitize_attachment_filename,
)


def _b64(text: str, *, encoding: str = "utf-8") -> str:
    return base64.urlsafe_b64encode(text.encode(encoding)).decode("ascii").rstrip("=")


def _headers(pairs: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"name": name, "value": value} for name, value in pairs]


def _attachment_part(
    filename: str,
    mime_type: str,
    *,
    attachment_id: str | None = None,
    size: int = 100,
    content_id: str | None = None,
    disposition: str = "attachment",
) -> dict[str, Any]:
    headers: list[tuple[str, str]] = [
        ("Content-Type", mime_type),
        ("Content-Disposition", f'{disposition}; filename="{filename}"'),
    ]
    if content_id:
        headers.append(("Content-ID", content_id))
    body: dict[str, Any] = {"size": size}
    if attachment_id:
        body["attachmentId"] = attachment_id
    return {
        "mimeType": mime_type,
        "filename": filename,
        "headers": _headers(headers),
        "body": body,
    }


def _message(payload: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "msg-1",
        "threadId": "thread-1",
        "labelIds": ["INBOX"],
        "snippet": "snippet text",
        "internalDate": "1690000000000",
        "sizeEstimate": 1234,
        "payload": payload,
    }
    base.update(overrides)
    return base


# 1. Plain text email -------------------------------------------------------


def test_plain_text_email() -> None:
    payload = {
        "mimeType": "text/plain",
        "headers": _headers(
            [
                ("From", "Alice <alice@example.com>"),
                ("To", "bob@example.com"),
                ("Subject", "Hello"),
                ("Date", "Mon, 01 Sep 2025 10:00:00 +0000"),
            ]
        ),
        "body": {"data": _b64("Hello world"), "size": 11},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body == "Hello world"
    assert dto.html_body is None
    assert dto.subject == "Hello"
    assert dto.sender == EmailAddressDto(
        email="alice@example.com", display_name="Alice"
    )
    assert dto.recipients == (
        EmailAddressDto(email="bob@example.com", display_name=None),
    )
    assert dto.date_header is not None


# 2. HTML-only email ----------------------------------------------------


def test_html_only_email() -> None:
    payload = {
        "mimeType": "text/html",
        "headers": _headers([("Subject", "Hi")]),
        "body": {"data": _b64("<p>Hi</p>"), "size": 9},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.html_body == "<p>Hi</p>"
    assert dto.text_body is None


# 3. multipart/alternative ------------------------------------------------


def test_multipart_alternative() -> None:
    payload = {
        "mimeType": "multipart/alternative",
        "headers": _headers([("Subject", "Alt")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "text/plain",
                "headers": _headers([]),
                "body": {"data": _b64("Plain"), "size": 5},
            },
            {
                "mimeType": "text/html",
                "headers": _headers([]),
                "body": {"data": _b64("<b>Html</b>"), "size": 11},
            },
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body == "Plain"
    assert dto.html_body == "<b>Html</b>"


# 4. multipart/mixed (body + attachment) ---------------------------------


def test_multipart_mixed_with_attachment() -> None:
    payload = {
        "mimeType": "multipart/mixed",
        "headers": _headers([("Subject", "Mixed")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "headers": _headers([]),
                "body": {"size": 0},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "headers": _headers([]),
                        "body": {"data": _b64("Body"), "size": 4},
                    },
                ],
            },
            _attachment_part(
                "report.pdf", "application/pdf", attachment_id="ATT1", size=2048
            ),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body == "Body"
    assert len(dto.attachments) == 1
    attachment = dto.attachments[0]
    assert attachment.filename == "report.pdf"
    assert attachment.attachment_id == "ATT1"
    assert attachment.is_inline is False


# 5. multipart/related (html + inline image) ------------------------------


def test_multipart_related_with_inline_image() -> None:
    payload = {
        "mimeType": "multipart/related",
        "headers": _headers([("Subject", "Related")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "text/html",
                "headers": _headers([]),
                "body": {"data": _b64('<img src="cid:img1">'), "size": 20},
            },
            _attachment_part(
                "image001.png",
                "image/png",
                attachment_id="ATT2",
                size=500,
                content_id="<img1>",
                disposition="inline",
            ),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.html_body == '<img src="cid:img1">'
    assert len(dto.attachments) == 1
    assert dto.attachments[0].is_inline is True
    assert dto.attachments[0].content_id == "<img1>"


# 6. Email with attachment (covered above); dedicated single-attachment case


def test_email_with_single_attachment() -> None:
    payload = {
        "mimeType": "multipart/mixed",
        "headers": _headers([("Subject", "One attachment")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "text/plain",
                "headers": _headers([]),
                "body": {"data": _b64("body"), "size": 4},
            },
            _attachment_part("notes.txt", "text/plain", attachment_id="A1"),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert len(dto.attachments) == 1
    assert dto.attachments[0].filename == "notes.txt"


# 7. Email with multiple attachments --------------------------------------


def test_email_with_multiple_attachments() -> None:
    payload = {
        "mimeType": "multipart/mixed",
        "headers": _headers([("Subject", "Multiple")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "text/plain",
                "headers": _headers([]),
                "body": {"data": _b64("body"), "size": 4},
            },
            _attachment_part("a.pdf", "application/pdf", attachment_id="A1"),
            _attachment_part(
                "b.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                attachment_id="A2",
            ),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    filenames = {attachment.filename for attachment in dto.attachments}
    assert filenames == {"a.pdf", "b.xlsx"}


# 8. Inline image (dedicated, without surrounding HTML) --------------------


def test_inline_image_marked_distinct_from_attachment() -> None:
    payload = {
        "mimeType": "multipart/related",
        "headers": _headers([("Subject", "Inline")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "text/html",
                "headers": _headers([]),
                "body": {"data": _b64("<p>see below</p>"), "size": 16},
            },
            _attachment_part(
                "logo.png",
                "image/png",
                attachment_id="LOGO",
                content_id="<logo1>",
                disposition="inline",
            ),
            _attachment_part("doc.pdf", "application/pdf", attachment_id="DOC"),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    inline = {a.filename: a.is_inline for a in dto.attachments}
    assert inline == {"logo.png": True, "doc.pdf": False}


# 9. Non-UTF8 charset -------------------------------------------------------


def test_non_utf8_charset_is_decoded() -> None:
    text = "café"
    payload = {
        "mimeType": "text/plain",
        "headers": _headers(
            [
                ("Subject", "Charset"),
                ("Content-Type", 'text/plain; charset="ISO-8859-1"'),
            ]
        ),
        "body": {
            "data": _b64(text, encoding="iso-8859-1"),
            "size": len(text.encode("iso-8859-1")),
        },
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body == "café"


# 10. Missing Subject -------------------------------------------------------


def test_missing_subject() -> None:
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([("From", "a@example.com")]),
        "body": {"data": _b64("x"), "size": 1},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.subject is None


# 11. Missing From -----------------------------------------------------------


def test_missing_from() -> None:
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([("Subject", "No sender")]),
        "body": {"data": _b64("x"), "size": 1},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.sender is None


# 12. Multiple recipients -----------------------------------------------------


def test_multiple_recipients() -> None:
    payload = {
        "mimeType": "text/plain",
        "headers": _headers(
            [
                (
                    "To",
                    'a@example.com, b@example.com, "C, Person" <c@example.com>',
                )
            ]
        ),
        "body": {"data": _b64("x"), "size": 1},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert [address.email for address in dto.recipients] == [
        "a@example.com",
        "b@example.com",
        "c@example.com",
    ]


# 13. Malformed MIME ----------------------------------------------------------


def test_malformed_mime_does_not_crash() -> None:
    dto = map_gmail_message_to_dto(_message({}))
    assert dto.text_body is None
    assert dto.html_body is None
    assert dto.attachments == ()


def test_invalid_base64_body_raises_for_caller_to_translate() -> None:
    # A single data character can never be valid base64 (even padded);
    # this documents that a truly corrupt body propagates so the adapter
    # boundary (GoogleGmailAdapter.get_message) can translate it into
    # GmailMessageParsingError rather than the batch retrieval crashing.
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([]),
        "body": {"data": "A", "size": 1},
    }
    with pytest.raises(Exception):  # noqa: B017 - documents the boundary
        map_gmail_message_to_dto(_message(payload))


def test_unusual_but_decodable_base64_does_not_crash() -> None:
    # base64.urlsafe_b64decode silently tolerates stray non-alphabet
    # characters (Python's default, non-validating decode); such input
    # must not raise, and should still produce *some* text rather than
    # crashing the whole message normalization.
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([]),
        "body": {"data": "not-valid-base64!!!", "size": 1},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body is not None


# 14. Large message (safety truncation) ---------------------------------------


def test_large_body_is_truncated_with_explicit_flag() -> None:
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([]),
        "body": {"data": _b64("x" * 50), "size": 5000},
    }
    dto = map_gmail_message_to_dto(_message(payload), max_body_bytes=1000)
    assert dto.text_body is None
    assert dto.content_truncated is True


# 15. Nested multipart structure ----------------------------------------------


def test_deeply_nested_multipart_structure() -> None:
    payload = {
        "mimeType": "multipart/mixed",
        "headers": _headers([("Subject", "Nested")]),
        "body": {"size": 0},
        "parts": [
            {
                "mimeType": "multipart/related",
                "headers": _headers([]),
                "body": {"size": 0},
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "headers": _headers([]),
                        "body": {"size": 0},
                        "parts": [
                            {
                                "mimeType": "text/plain",
                                "headers": _headers([]),
                                "body": {"data": _b64("Plain"), "size": 5},
                            },
                            {
                                "mimeType": "text/html",
                                "headers": _headers([]),
                                "body": {"data": _b64("<p>Html</p>"), "size": 11},
                            },
                        ],
                    },
                    _attachment_part(
                        "inline.png",
                        "image/png",
                        attachment_id="IMG1",
                        content_id="<inline1>",
                        disposition="inline",
                    ),
                ],
            },
            _attachment_part("doc.pdf", "application/pdf", attachment_id="DOC1"),
        ],
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.text_body == "Plain"
    assert dto.html_body == "<p>Html</p>"
    inline = {a.filename: a.is_inline for a in dto.attachments}
    assert inline == {"inline.png": True, "doc.pdf": False}


# Header/date/filename helper coverage ---------------------------------------


def test_decode_mime_words_handles_rfc2047_encoded_name() -> None:
    encoded = "=?UTF-8?B?QWxpY2U=?= <alice@example.com>"
    payload = {
        "mimeType": "text/plain",
        "headers": _headers([("From", encoded)]),
        "body": {"data": _b64("x"), "size": 1},
    }
    dto = map_gmail_message_to_dto(_message(payload))
    assert dto.sender is not None
    assert dto.sender.display_name == "Alice"


def test_decode_mime_words_passthrough_for_plain_text() -> None:
    assert decode_mime_words("Plain Name") == "Plain Name"


def test_parse_internal_date_converts_epoch_millis_to_utc() -> None:
    parsed = parse_internal_date("1690000000000")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.isoformat().endswith("+00:00")


def test_parse_internal_date_handles_missing_value() -> None:
    assert parse_internal_date(None) is None
    assert parse_internal_date("not-a-number") is None


def test_parse_date_header_returns_none_for_garbage() -> None:
    assert parse_date_header("not a date") is None
    assert parse_date_header(None) is None


def test_sanitize_attachment_filename_strips_path_components() -> None:
    assert sanitize_attachment_filename("../../evil.exe") == "evil.exe"
    assert sanitize_attachment_filename("C:\\temp\\report.pdf") == "report.pdf"
