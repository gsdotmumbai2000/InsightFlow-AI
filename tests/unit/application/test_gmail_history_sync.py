"""GmailHistorySyncService tests (Phase 10) — fakes only, no network."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.commands.events import CreateIntelligenceEventUseCase
from insightflow.application.commands.gmail import (
    IngestTopicMessagesUseCase,
    RetrieveTopicMessagesUseCase,
)
from insightflow.application.dto.email import EmailAddressDto, EmailMessageDto
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailHistoryRecordDto,
)
from insightflow.application.exceptions.gmail import GmailHistoryUnavailableError
from insightflow.application.services.gmail_history_sync import GmailHistorySyncService
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import IntelligenceEventCreated


def _build_service(
    store: InMemoryStore,
    gmail: FakeGmailAdapter,
    *,
    batch_size: int = 50,
    on_event_created: Callable[[IntelligenceEventCreated], None] | None = None,
) -> GmailHistorySyncService:
    create_event = CreateIntelligenceEventUseCase(store.unit_of_work_factory)
    retrieve = RetrieveTopicMessagesUseCase(store.unit_of_work_factory, gmail, gmail)
    ingest = IngestTopicMessagesUseCase(
        store.unit_of_work_factory, retrieve, create_event
    )
    return GmailHistorySyncService(
        store.unit_of_work_factory,
        gmail,
        gmail,
        ingest,
        batch_size=batch_size,
        on_event_created=on_event_created,
    )


def _map_topic(
    use_cases: ApplicationUseCases,
    gmail: FakeGmailAdapter,
    *,
    label_id: str = "Label_TRUMP",
    topic_name: str = "TRUMP",
) -> str:
    use_cases.connect_gmail.execute()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id=label_id, topic_name=topic_name)
    )
    return mapping.topic_id


def _email(message_id: str, *, label_ids: tuple[str, ...]) -> EmailMessageDto:
    return EmailMessageDto(
        provider="GMAIL",
        external_message_id=message_id,
        thread_id=f"thread-{message_id}",
        subject="Alert",
        sender=EmailAddressDto(email="alerts@google.com"),
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
        text_body="body",
        html_body=None,
        label_ids=label_ids,
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def test_monitored_label_creates_event(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("INBOX", "Label_TRUMP"))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token=None,
            history_id="101",
        )
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.created_count == 1
    assert outcome.duplicate_count == 0
    assert outcome.failed_count == 0
    assert outcome.new_history_id == "101"
    events = store.events.list_recent()
    assert len(events) == 1


def test_unmonitored_label_is_ignored(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("INBOX", "PERSONAL"))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token=None,
            history_id="101",
        )
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.created_count == 0
    assert outcome.processed_message_count == 0
    assert store.events.list_recent() == []


def test_pagination_collects_candidates_across_pages(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.messages_by_id["m2"] = _email("m2", label_ids=("Label_TRUMP",))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token="1",
        ),
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m2", history_id="102"),),
            next_page_token=None,
            history_id="102",
        ),
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.created_count == 2
    assert outcome.new_history_id == "102"
    assert outcome.has_more is False


def test_batch_limit_truncates_and_advances_cursor_safely(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.messages_by_id["m2"] = _email("m2", label_ids=("Label_TRUMP",))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(
                GmailHistoryRecordDto(message_id="m1", history_id="101"),
                GmailHistoryRecordDto(message_id="m2", history_id="102"),
            ),
            next_page_token=None,
            history_id="102",
        ),
    ]
    service = _build_service(store, gmail, batch_size=1)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    # Only the first candidate was processed; cursor must reflect that
    # exact position, not the page's final historyId (102), so a follow-up
    # sync() picks up m2 rather than silently skipping it.
    assert outcome.created_count == 1
    assert outcome.has_more is True
    assert outcome.new_history_id == "101"
    assert gmail.get_calls == ["m1"]


def test_duplicate_message_id_within_page_is_deduplicated(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(
                GmailHistoryRecordDto(message_id="m1", history_id="101"),
                GmailHistoryRecordDto(message_id="m1", history_id="102"),
            ),
            next_page_token=None,
            history_id="102",
        ),
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.created_count == 1
    assert gmail.get_calls == ["m1"]


def test_malformed_message_does_not_abort_history_sync(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.messages_by_id["m3"] = _email("m3", label_ids=("Label_TRUMP",))
    gmail.fail_message_ids = {"m2"}
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(
                GmailHistoryRecordDto(message_id="m1", history_id="101"),
                GmailHistoryRecordDto(message_id="m2", history_id="102"),
                GmailHistoryRecordDto(message_id="m3", history_id="103"),
            ),
            next_page_token=None,
            history_id="103",
        ),
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.created_count == 2
    assert outcome.failed_count == 1
    assert outcome.new_history_id == "103"


def test_history_unavailable_propagates_to_caller(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.unavailable_history_ids = {"999"}
    service = _build_service(store, gmail)

    with pytest.raises(GmailHistoryUnavailableError):
        service.sync(account_id="user@example.com", start_history_id="999")


def test_no_candidates_returns_empty_outcome(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(records=(), next_page_token=None, history_id="100")
    ]
    service = _build_service(store, gmail)

    outcome = service.sync(account_id="user@example.com", start_history_id="100")

    assert outcome.processed_message_count == 0
    assert outcome.new_history_id == "100"


def test_on_event_created_fires_once_for_a_new_event(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    """Phase 12: the real-time history-sync path notifies on new events."""
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token=None,
            history_id="101",
        )
    ]
    received: list[IntelligenceEventCreated] = []
    service = _build_service(store, gmail, on_event_created=received.append)

    service.sync(account_id="user@example.com", start_history_id="100")

    assert len(received) == 1


def test_on_event_created_does_not_fire_for_duplicates(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _map_topic(use_cases, gmail)
    gmail.messages_by_id["m1"] = _email("m1", label_ids=("Label_TRUMP",))
    gmail.history_pages_by_start_id["100"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token=None,
            history_id="101",
        )
    ]
    received: list[IntelligenceEventCreated] = []
    service = _build_service(store, gmail, on_event_created=received.append)
    service.sync(account_id="user@example.com", start_history_id="100")
    assert len(received) == 1

    # Same message delivered again (e.g. duplicate Pub/Sub notification).
    gmail.history_pages_by_start_id["101"] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="101"),),
            next_page_token=None,
            history_id="101",
        )
    ]
    service.sync(account_id="user@example.com", start_history_id="101")

    assert len(received) == 1
