"""GmailFullSyncService tests (Phase 10) — fakes only, no network."""

from __future__ import annotations

from collections.abc import Callable

from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.commands.events import CreateIntelligenceEventUseCase
from insightflow.application.commands.gmail import (
    IngestTopicMessagesUseCase,
    RetrieveTopicMessagesUseCase,
)
from insightflow.application.dto.email import EmailAddressDto, EmailMessageDto
from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.services.gmail_full_sync import GmailFullSyncService
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import IntelligenceEventCreated


def _email(message_id: str, *, label_id: str) -> EmailMessageDto:
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
        label_ids=(label_id,),
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def _build_service(
    store: InMemoryStore,
    gmail: FakeGmailAdapter,
    *,
    max_messages: int = 50,
    on_event_created: Callable[[IntelligenceEventCreated], None] | None = None,
) -> GmailFullSyncService:
    create_event = CreateIntelligenceEventUseCase(store.unit_of_work_factory)
    retrieve = RetrieveTopicMessagesUseCase(store.unit_of_work_factory, gmail, gmail)
    ingest = IngestTopicMessagesUseCase(
        store.unit_of_work_factory, retrieve, create_event
    )
    return GmailFullSyncService(
        store.unit_of_work_factory,
        ingest,
        max_messages_per_topic=max_messages,
        on_event_created=on_event_created,
    )


def test_full_sync_covers_all_monitored_topics(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    mapping_a = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    mapping_b = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_B", topic_name="MODI")
    )
    gmail.message_ids_by_label["Label_A"] = ["a1"]
    gmail.message_ids_by_label["Label_B"] = ["b1"]
    gmail.messages_by_id = {
        "a1": _email("a1", label_id="Label_A"),
        "b1": _email("b1", label_id="Label_B"),
    }

    service = _build_service(store, gmail)
    outcome = service.sync_all_monitored_topics()

    assert outcome.topic_count == 2
    assert outcome.created_count == 2
    assert outcome.errors == ()
    events = store.events.list_recent()
    topic_ids = {e.topic_id.value for e in events if e.topic_id is not None}
    assert topic_ids == {mapping_a.topic_id, mapping_b.topic_id}


def test_full_sync_is_idempotent(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.message_ids_by_label["Label_A"] = ["a1"]
    gmail.messages_by_id = {"a1": _email("a1", label_id="Label_A")}

    service = _build_service(store, gmail)
    service.sync_all_monitored_topics()
    second = service.sync_all_monitored_topics()

    assert second.created_count == 0
    assert second.duplicate_count == 1
    assert len(store.events.list_recent()) == 1


def test_full_sync_ignores_disabled_topics(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    mapping = use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    use_cases.disable_topic.execute(mapping.topic_id)
    gmail.message_ids_by_label["Label_A"] = ["a1"]
    gmail.messages_by_id = {"a1": _email("a1", label_id="Label_A")}

    service = _build_service(store, gmail)
    outcome = service.sync_all_monitored_topics()

    assert outcome.topic_count == 0
    assert store.events.list_recent() == []


def test_full_sync_no_monitored_topics_is_a_noop(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    service = _build_service(store, gmail)
    outcome = service.sync_all_monitored_topics()
    assert outcome.topic_count == 0
    assert outcome.created_count == 0


def test_on_event_created_fires_once_per_new_event(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    """Phase 12: the real-time full-sync path notifies on new events."""
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.message_ids_by_label["Label_A"] = ["a1"]
    gmail.messages_by_id = {"a1": _email("a1", label_id="Label_A")}
    received: list[IntelligenceEventCreated] = []
    service = _build_service(store, gmail, on_event_created=received.append)

    service.sync_all_monitored_topics()

    assert len(received) == 1


def test_on_event_created_does_not_fire_for_duplicates_on_resync(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.message_ids_by_label["Label_A"] = ["a1"]
    gmail.messages_by_id = {"a1": _email("a1", label_id="Label_A")}
    received: list[IntelligenceEventCreated] = []
    service = _build_service(store, gmail, on_event_created=received.append)

    service.sync_all_monitored_topics()
    service.sync_all_monitored_topics()

    assert len(received) == 1
