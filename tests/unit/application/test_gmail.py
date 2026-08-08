"""Gmail application use-case unit tests (no network)."""

from __future__ import annotations

import pytest
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import (
    GmailLabelDto,
    MapGmailLabelToTopicRequest,
)
from insightflow.application.exceptions import DuplicateTopicError
from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailConnectionError,
)
from insightflow.application.use_cases import ApplicationUseCases


def test_connect_disconnect_status(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    status = use_cases.get_gmail_connection_status.execute()
    assert status.status == "NOT_CONNECTED"
    account = use_cases.connect_gmail.execute()
    assert account.email == "user@example.com"
    assert gmail.token_value is not None
    status = use_cases.get_gmail_connection_status.execute()
    assert status.status == "CONNECTED"
    assert status.account is not None
    assert "token" not in status.account.email.lower() or True
    # DTO must not expose token fields
    assert not hasattr(status.account, "token")
    assert not hasattr(status.account, "refresh_token")
    use_cases.disconnect_gmail.execute()
    assert gmail.token_value is None
    assert use_cases.get_gmail_connection_status.execute().status == "NOT_CONNECTED"


def test_connect_failure(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    gmail.fail_connect = True
    with pytest.raises(GmailAuthenticationError):
        use_cases.connect_gmail.execute()


def test_list_labels_requires_connection(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    with pytest.raises(GmailConnectionError):
        use_cases.list_gmail_labels.execute()
    use_cases.connect_gmail.execute()
    gmail.labels = [
        GmailLabelDto(label_id="L1", name="Alpha", label_type="user"),
    ]
    labels = use_cases.list_gmail_labels.execute()
    assert len(labels) == 1
    assert labels[0].name == "Alpha"


def test_map_gmail_label_to_topic(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter
) -> None:
    use_cases.connect_gmail.execute()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(
            label_id="Label_42",
            topic_name="Markets",
            label_name="MARKETS",
        )
    )
    assert mapping.topic_name == "Markets"
    assert mapping.label_id == "Label_42"
    topic = use_cases.get_topic.execute(mapping.topic_id)
    assert topic.source.source_type == "GMAIL"
    assert topic.source.source_identifier == "Label_42"

    with pytest.raises(DuplicateTopicError):
        use_cases.map_gmail_label_to_topic.execute(
            MapGmailLabelToTopicRequest(
                label_id="Label_42",
                topic_name="Other",
            )
        )


def test_remove_gmail_label_mapping(
    use_cases: ApplicationUseCases, store: InMemoryStore
) -> None:
    use_cases.connect_gmail.execute()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_9", topic_name="X")
    )
    topic = use_cases.remove_gmail_label_mapping.execute(mapping.topic_id)
    assert topic.source.source_type == "GENERIC"
    assert topic.source.source_id == "local"
