"""IngestTopicMessagesUseCase tests (fake Gmail provider, no network)."""

from __future__ import annotations

import logging

import pytest
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort

from insightflow.application.commands.gmail import (
    _compute_content_hash,
    _email_message_to_create_event_request,
    _normalize_content,
    _strip_html,
)
from insightflow.application.dto.email import (
    EmailAddressDto,
    EmailAttachmentDto,
    EmailMessageDto,
    IngestTopicMessagesRequest,
)
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.exceptions import TopicNotGmailConfiguredError
from insightflow.application.use_cases import ApplicationUseCases


def _email(
    message_id: str,
    *,
    subject: str = "Alert",
    text_body: str | None = "Plain body content",
    html_body: str | None = None,
    attachments: tuple[EmailAttachmentDto, ...] = (),
) -> EmailMessageDto:
    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=message_id,
        thread_id=f"thread-{message_id}",
        subject=subject,
        sender=EmailAddressDto(email="alerts@google.com", display_name="Google Alerts"),
        recipients=(),
        cc=(),
        bcc=(),
        reply_to=(),
        message_id_header=None,
        in_reply_to=None,
        references=(),
        received_at=None,
        date_header=None,
        snippet="snippet",
        text_body=text_body,
        html_body=html_body,
        label_ids=("Label_1",),
        attachments=attachments,
        size_estimate=100,
        history_id="1",
        content_truncated=False,
    )


def _make_gmail_topic(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    *,
    label_id: str = "Label_1",
) -> str:
    use_cases.connect_gmail.execute()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id=label_id, topic_name="TRUMP")
    )
    return mapping.topic_id


# -- Pure normalization helpers -----------------------------------------------


def test_strip_html_removes_tags_and_scripts() -> None:
    html = "<html><head><style>.x{}</style></head><body><p>Hello <b>World</b></p>"
    html += "<script>evil()</script></body></html>"
    text = _strip_html(html)
    assert "Hello" in text
    assert "World" in text
    assert "evil" not in text
    assert "<" not in text


def test_normalize_content_prefers_plain_text() -> None:
    message = _email("m1", text_body="Plain text", html_body="<p>HTML</p>")
    assert _normalize_content(message) == "Plain text"


def test_normalize_content_falls_back_to_html() -> None:
    message = _email("m1", text_body=None, html_body="<p>Only HTML</p>")
    assert _normalize_content(message) == "Only HTML"


def test_normalize_content_none_when_no_body() -> None:
    message = _email("m1", text_body=None, html_body=None)
    assert _normalize_content(message) is None


def test_content_hash_deterministic_and_none_for_empty() -> None:
    assert _compute_content_hash(None) is None
    assert _compute_content_hash("") is None
    h1 = _compute_content_hash("same text")
    h2 = _compute_content_hash("same text")
    assert h1 == h2
    assert h1 != _compute_content_hash("different text")


def test_email_message_to_create_event_request_maps_fields() -> None:
    message = _email("m42", subject="Breaking News", text_body="Body text")
    request = _email_message_to_create_event_request(
        message, topic_id="topic-1", account_id="user@example.com"
    )
    assert request.source_type == "GMAIL"
    assert request.source_id == "user@example.com"
    assert request.account_id == "user@example.com"
    assert request.external_id == "m42"
    assert request.thread_id == "thread-m42"
    assert request.topic_id == "topic-1"
    assert request.title == "Breaking News"
    assert request.normalized_content == "Body text"
    assert request.url == "https://mail.google.com/mail/u/0/#all/m42"
    assert request.content_hash == _compute_content_hash("Body text")
    assert request.received_at is None  # left to ingestion-time default


# -- IngestTopicMessagesUseCase ------------------------------------------------


def test_topic_without_gmail_mapping_raises(use_cases: ApplicationUseCases) -> None:
    from insightflow.application.dto.models import CreateTopicRequest

    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Manual",
            source_type="GENERIC",
            source_id="local",
            source_identifier="manual-1",
        )
    )
    with pytest.raises(TopicNotGmailConfiguredError):
        use_cases.ingest_topic_messages.execute(
            IngestTopicMessagesRequest(topic_id=topic.id)
        )


def test_ingest_creates_events_and_persists_fields(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1", "m2"]
    gmail.messages_by_id = {
        "m1": _email("m1", subject="First"),
        "m2": _email("m2", subject="Second"),
    }

    result = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert len(result.created) == 2
    assert result.duplicate_count == 0
    assert result.failed == ()
    event = use_cases.get_intelligence_event.execute(result.created[0].event_id)
    assert event.topic_id == topic_id
    assert event.source.source_type == "GMAIL"
    assert event.source.external_id in ("m1", "m2")
    assert event.title in ("First", "Second")
    assert event.content_hash is not None
    assert len(result.domain_events) == 2
    assert {e.event_id.value for e in result.domain_events} == {
        c.event_id for c in result.created
    }


def test_ingest_is_idempotent_on_rerun(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1", "m2"]
    gmail.messages_by_id = {"m1": _email("m1"), "m2": _email("m2")}

    first = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )
    second = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert len(first.created) == 2
    assert second.created == ()
    assert second.duplicate_count == 2
    assert second.domain_events == ()


def test_ingest_persists_non_inline_attachments_only(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    attachments = (
        EmailAttachmentDto(
            filename="report.pdf",
            mime_type="application/pdf",
            attachment_id="A1",
            size_estimate=1000,
            is_inline=False,
        ),
        EmailAttachmentDto(
            filename="logo.png",
            mime_type="image/png",
            attachment_id="A2",
            size_estimate=200,
            is_inline=True,
            content_id="<logo1>",
        ),
    )
    gmail.message_ids_by_label["Label_1"] = ["m1"]
    gmail.messages_by_id = {"m1": _email("m1", attachments=attachments)}

    result = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert len(result.created) == 1
    assert result.created[0].attachment_count == 1
    stored = use_cases.list_event_attachments.execute(result.created[0].event_id)
    assert len(stored) == 1
    assert stored[0].filename == "report.pdf"


def test_ingest_malformed_message_does_not_abort_batch(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    ids = ["m1", "m2", "m3"]
    gmail.message_ids_by_label["Label_1"] = ids
    gmail.messages_by_id = {mid: _email(mid) for mid in ids}
    gmail.fail_message_ids = {"m2"}

    result = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert {c.external_message_id for c in result.created} == {"m1", "m3"}
    assert len(result.failed) == 1
    assert result.failed[0].message_id == "m2"


def test_ingest_max_messages_reports_has_more(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    ids = [f"m{i}" for i in range(10)]
    gmail.message_ids_by_label["Label_1"] = ids
    gmail.messages_by_id = {mid: _email(mid) for mid in ids}

    result = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=3)
    )

    assert len(result.created) == 3
    assert result.has_more is True


def test_manual_ingestion_does_not_trigger_toast_notification(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    notification_port: FakeNotificationPort,
) -> None:
    """Phase 12: manual "Save recent messages" must never produce a toast.

    ``IngestTopicMessagesUseCase`` (used directly by the Topics page's
    "Save recent messages" action) is only ever wired to the Phase 11 AI
    dispatcher, never to ``ToastNotificationDispatcher`` — that hook lives
    one layer up, in the real-time-only ``GmailHistorySyncService``/
    ``GmailFullSyncService``.
    """
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1"]
    gmail.messages_by_id = {"m1": _email("m1", subject="First")}

    result = use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert len(result.created) == 1
    assert notification_port.requests == []


def test_listing_existing_events_never_triggers_notification(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    notification_port: FakeNotificationPort,
) -> None:
    """Phase 12: reading already-persisted events (e.g. app startup) is silent."""
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1"]
    gmail.messages_by_id = {"m1": _email("m1", subject="First")}
    use_cases.ingest_topic_messages.execute(
        IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )
    notification_port.requests.clear()  # only the manual-ingest path is asserted above

    use_cases.list_recent_intelligence_events.execute(limit=10)
    use_cases.list_events_by_topic.execute(topic_id, limit=10)

    assert notification_port.requests == []


def test_ingest_never_logs_email_body_content(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1"]
    gmail.messages_by_id = {
        "m1": _email("m1", text_body="super secret private body content")
    }

    with caplog.at_level(logging.DEBUG):
        use_cases.ingest_topic_messages.execute(
            IngestTopicMessagesRequest(topic_id=topic_id, max_messages=10)
        )

    for record in caplog.records:
        assert "secret private body" not in record.getMessage()
