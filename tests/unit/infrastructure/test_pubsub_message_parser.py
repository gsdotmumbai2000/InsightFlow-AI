"""Gmail Pub/Sub notification parsing tests (Phase 10)."""

from __future__ import annotations

from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)


def test_parses_valid_payload() -> None:
    data = b'{"emailAddress": "user@example.com", "historyId": "12345"}'
    notification = parse_gmail_pubsub_notification(data)
    assert notification is not None
    assert notification.email_address == "user@example.com"
    assert notification.history_id == "12345"


def test_history_id_coerced_to_string() -> None:
    data = b'{"emailAddress": "user@example.com", "historyId": 12345}'
    notification = parse_gmail_pubsub_notification(data)
    assert notification is not None
    assert notification.history_id == "12345"


def test_malformed_json_returns_none() -> None:
    assert parse_gmail_pubsub_notification(b"not json") is None


def test_non_utf8_bytes_returns_none() -> None:
    assert parse_gmail_pubsub_notification(b"\xff\xfe\x00\x01") is None


def test_missing_email_address_returns_none() -> None:
    data = b'{"historyId": "12345"}'
    assert parse_gmail_pubsub_notification(data) is None


def test_missing_history_id_returns_none() -> None:
    data = b'{"emailAddress": "user@example.com"}'
    assert parse_gmail_pubsub_notification(data) is None


def test_non_object_json_returns_none() -> None:
    assert parse_gmail_pubsub_notification(b"[1, 2, 3]") is None


def test_never_includes_subject_or_body_semantics() -> None:
    """The notification is a change signal only — confirm the DTO has no
    body/subject-shaped fields even if an attacker-controlled payload
    includes extra keys."""
    data = (
        b'{"emailAddress": "user@example.com", "historyId": "1", '
        b'"subject": "should be ignored", "body": "should be ignored"}'
    )
    notification = parse_gmail_pubsub_notification(data)
    assert notification is not None
    assert not hasattr(notification, "subject")
    assert not hasattr(notification, "body")
