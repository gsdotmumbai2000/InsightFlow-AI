"""RetrieveTopicMessagesUseCase tests (fake Gmail provider, no network)."""

from __future__ import annotations

import logging

import pytest
from tests.fakes.gmail import FakeGmailAdapter

from insightflow.application.dto.email import (
    EmailAddressDto,
    EmailMessageDto,
    RetrieveTopicMessagesRequest,
)
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.dto.models import CreateTopicRequest
from insightflow.application.exceptions import (
    GmailConnectionError,
    TopicNotFoundError,
    TopicNotGmailConfiguredError,
)
from insightflow.application.use_cases import ApplicationUseCases


def _email(message_id: str, *, subject: str = "Subject") -> EmailMessageDto:
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
        text_body="body text — private content",
        html_body=None,
        label_ids=("Label_1",),
        attachments=(),
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


def test_topic_without_gmail_mapping_raises(
    use_cases: ApplicationUseCases,
) -> None:
    topic = use_cases.create_topic.execute(
        CreateTopicRequest(
            name="Manual",
            description=None,
            source_type="GENERIC",
            source_id="local",
            source_identifier="manual-1",
            ai_profile_id=None,
        )
    )
    with pytest.raises(TopicNotGmailConfiguredError):
        use_cases.retrieve_topic_messages.execute(
            RetrieveTopicMessagesRequest(topic_id=topic.id)
        )


def test_unknown_topic_raises_not_found(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(TopicNotFoundError):
        use_cases.retrieve_topic_messages.execute(
            RetrieveTopicMessagesRequest(topic_id="missing-id")
        )


def test_disconnected_gmail_raises_connection_error(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    use_cases.disconnect_gmail.execute()
    with pytest.raises(GmailConnectionError):
        use_cases.retrieve_topic_messages.execute(
            RetrieveTopicMessagesRequest(topic_id=topic_id)
        )


def test_successful_retrieval_returns_normalized_messages(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1", "m2", "m3"]
    gmail.messages_by_id = {mid: _email(mid) for mid in ["m1", "m2", "m3"]}

    result = use_cases.retrieve_topic_messages.execute(
        RetrieveTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    assert result.label_id == "Label_1"
    assert [msg.external_message_id for msg in result.messages] == ["m1", "m2", "m3"]
    assert result.failed == ()
    assert result.has_more is False


def test_pagination_across_multiple_pages(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    ids = [f"m{i}" for i in range(12)]
    gmail.message_ids_by_label["Label_1"] = ids
    gmail.messages_by_id = {mid: _email(mid) for mid in ids}
    gmail.list_page_size = 5  # forces multiple messages.list pages

    result = use_cases.retrieve_topic_messages.execute(
        RetrieveTopicMessagesRequest(topic_id=topic_id, max_messages=12)
    )

    assert [msg.external_message_id for msg in result.messages] == ids
    assert gmail.list_calls >= 3
    assert result.has_more is False


def test_max_messages_limit_stops_cleanly_and_reports_more(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    ids = [f"m{i}" for i in range(20)]
    gmail.message_ids_by_label["Label_1"] = ids
    gmail.messages_by_id = {mid: _email(mid) for mid in ids}

    result = use_cases.retrieve_topic_messages.execute(
        RetrieveTopicMessagesRequest(topic_id=topic_id, max_messages=5)
    )

    assert len(result.messages) == 5
    assert result.has_more is True
    # Never retrieves more full messages than the bounded limit.
    assert len(gmail.get_calls) == 5


def test_malformed_message_does_not_abort_batch(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    ids = [f"m{i}" for i in range(1, 6)]
    gmail.message_ids_by_label["Label_1"] = ids
    gmail.messages_by_id = {mid: _email(mid) for mid in ids}
    gmail.fail_message_ids = {"m3"}

    result = use_cases.retrieve_topic_messages.execute(
        RetrieveTopicMessagesRequest(topic_id=topic_id, max_messages=10)
    )

    retrieved_ids = [msg.external_message_id for msg in result.messages]
    assert retrieved_ids == ["m1", "m2", "m4", "m5"]
    assert len(result.failed) == 1
    assert result.failed[0].message_id == "m3"


def test_retrieval_never_logs_email_body_content(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    topic_id = _make_gmail_topic(use_cases, gmail)
    gmail.message_ids_by_label["Label_1"] = ["m1"]
    gmail.messages_by_id = {"m1": _email("m1")}

    with caplog.at_level(logging.DEBUG):
        use_cases.retrieve_topic_messages.execute(
            RetrieveTopicMessagesRequest(topic_id=topic_id, max_messages=10)
        )

    for record in caplog.records:
        assert "private content" not in record.getMessage()
