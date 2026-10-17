"""GmailPubSubNotificationProcessor tests (Phase 10) — fakes only."""

from __future__ import annotations

import threading
import time

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
    HistorySyncOutcome,
    PubSubNotificationDto,
)
from insightflow.application.services.gmail_full_sync import GmailFullSyncService
from insightflow.application.services.gmail_history_sync import GmailHistorySyncService
from insightflow.application.services.gmail_pubsub_processor import (
    GmailPubSubNotificationProcessor,
)
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.domain import SourceType

ACCOUNT_ID = "user@example.com"


def _email(message_id: str) -> EmailMessageDto:
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
        label_ids=("Label_TRUMP",),
        attachments=(),
        size_estimate=10,
        history_id="1",
        content_truncated=False,
    )


def _build_processor(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> GmailPubSubNotificationProcessor:
    create_event = CreateIntelligenceEventUseCase(store.unit_of_work_factory)
    retrieve = RetrieveTopicMessagesUseCase(store.unit_of_work_factory, gmail, gmail)
    ingest = IngestTopicMessagesUseCase(
        store.unit_of_work_factory, retrieve, create_event
    )
    history_sync = GmailHistorySyncService(
        store.unit_of_work_factory, gmail, gmail, ingest
    )
    full_sync = GmailFullSyncService(store.unit_of_work_factory, ingest)
    watch_lifecycle = GmailWatchLifecycleService(
        store.unit_of_work_factory,
        gmail,
        pubsub_project_id="test-project",
        pubsub_topic_name="gmail-topic",
        pubsub_subscription="gmail-sub",
    )
    return GmailPubSubNotificationProcessor(
        store.unit_of_work_factory, history_sync, full_sync, watch_lifecycle
    )


def _setup_topic_and_watch(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    watch_lifecycle = GmailWatchLifecycleService(
        store.unit_of_work_factory,
        gmail,
        pubsub_project_id="test-project",
        pubsub_topic_name="gmail-topic",
        pubsub_subscription="gmail-sub",
    )
    watch_lifecycle.establish_watch(account_id=ACCOUNT_ID)


def test_no_monitoring_state_triggers_full_sync(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_TRUMP", topic_name="TRUMP")
    )
    gmail.message_ids_by_label["Label_TRUMP"] = ["m1"]
    gmail.messages_by_id = {"m1": _email("m1")}
    processor = _build_processor(store, gmail)

    result = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="500")
    )

    assert result is True
    assert len(store.events.list_recent()) == 1
    with store.unit_of_work_factory() as uow:
        state = uow.monitoring_states.get_by_account(
            account_id=ACCOUNT_ID, provider=SourceType.GMAIL
        )
    assert state is not None
    assert state.current_history_id == gmail.watch_history_id


def test_successful_sync_advances_state_and_records_notification(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    gmail.messages_by_id["m1"] = _email("m1")
    gmail.history_pages_by_start_id[gmail.watch_history_id] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="600"),),
            next_page_token=None,
            history_id="600",
        )
    ]
    processor = _build_processor(store, gmail)

    result = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="600")
    )

    assert result is True
    with store.unit_of_work_factory() as uow:
        state = uow.monitoring_states.get_by_account(
            account_id=ACCOUNT_ID, provider=SourceType.GMAIL
        )
    assert state is not None
    assert state.current_history_id == "600"
    assert state.last_notification_at is not None
    assert state.status.value == "RUNNING"
    assert len(store.events.list_recent()) == 1


def test_duplicate_notification_is_idempotent(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    gmail.messages_by_id["m1"] = _email("m1")
    gmail.history_pages_by_start_id[gmail.watch_history_id] = [
        GmailHistoryPageDto(
            records=(GmailHistoryRecordDto(message_id="m1", history_id="600"),),
            next_page_token=None,
            history_id="600",
        )
    ]
    # A second (duplicate) notification re-delivers the same history range;
    # the stored cursor already covers it, so history.list("600") returns
    # nothing new — simulate that explicitly.
    gmail.history_pages_by_start_id["600"] = [
        GmailHistoryPageDto(records=(), next_page_token=None, history_id="600")
    ]
    processor = _build_processor(store, gmail)

    first = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="600")
    )
    second = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="600")
    )

    assert first is True
    assert second is True
    assert len(store.events.list_recent()) == 1


def test_history_unavailable_falls_back_to_full_sync(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    gmail.message_ids_by_label["Label_TRUMP"] = ["m1"]
    gmail.messages_by_id["m1"] = _email("m1")
    gmail.unavailable_history_ids = {gmail.watch_history_id}
    processor = _build_processor(store, gmail)

    result = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="700")
    )

    assert result is True
    assert len(store.events.list_recent()) == 1
    assert gmail.stop_watch_calls == 0
    assert len(gmail.watch_calls) == 2  # initial setup + recovery re-baseline


def test_transient_failure_marks_error_and_does_not_acknowledge(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    # No history page registered for this start id -> FakeGmailAdapter
    # returns an empty page (not an error), so force a real failure by
    # disconnecting Gmail after watch setup: get_message calls will raise.
    gmail.connected = False
    processor = _build_processor(store, gmail)

    result = processor.process(
        PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="800")
    )

    assert result is False
    with store.unit_of_work_factory() as uow:
        state = uow.monitoring_states.get_by_account(
            account_id=ACCOUNT_ID, provider=SourceType.GMAIL
        )
    assert state is not None
    assert state.status.value == "ERROR"
    assert state.last_error is not None


def test_record_worker_error_sets_last_error_without_changing_status(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    processor = _build_processor(store, gmail)

    processor.record_worker_error(ACCOUNT_ID, "Pub/Sub pull failed: RuntimeError")

    with store.unit_of_work_factory() as uow:
        state = uow.monitoring_states.get_by_account(
            account_id=ACCOUNT_ID, provider=SourceType.GMAIL
        )
    assert state is not None
    assert state.last_error == "Pub/Sub pull failed: RuntimeError"
    # Established but never started via StartMonitoringUseCase in this
    # test, so status is whatever establish_watch left it at — the point
    # is record_worker_error must not have forced it to ERROR.
    assert state.status.value != "ERROR"


def test_record_worker_error_is_a_noop_when_no_state_exists(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    processor = _build_processor(store, gmail)

    processor.record_worker_error(ACCOUNT_ID, "Pub/Sub pull failed: RuntimeError")

    with store.unit_of_work_factory() as uow:
        state = uow.monitoring_states.get_by_account(
            account_id=ACCOUNT_ID, provider=SourceType.GMAIL
        )
    assert state is None


def test_concurrent_notifications_are_serialized(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    _setup_topic_and_watch(use_cases, gmail, store)
    active = 0
    max_active = 0
    lock = threading.Lock()

    class SlowHistorySync(GmailHistorySyncService):
        def sync(self, *, account_id: str, start_history_id: str) -> HistorySyncOutcome:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1
            return HistorySyncOutcome(new_history_id=start_history_id)

    create_event = CreateIntelligenceEventUseCase(store.unit_of_work_factory)
    retrieve = RetrieveTopicMessagesUseCase(store.unit_of_work_factory, gmail, gmail)
    ingest = IngestTopicMessagesUseCase(
        store.unit_of_work_factory, retrieve, create_event
    )
    slow_sync = SlowHistorySync(store.unit_of_work_factory, gmail, gmail, ingest)
    full_sync = GmailFullSyncService(store.unit_of_work_factory, ingest)
    watch_lifecycle = GmailWatchLifecycleService(
        store.unit_of_work_factory,
        gmail,
        pubsub_project_id="test-project",
        pubsub_topic_name="gmail-topic",
        pubsub_subscription="gmail-sub",
    )
    processor = GmailPubSubNotificationProcessor(
        store.unit_of_work_factory, slow_sync, full_sync, watch_lifecycle
    )

    threads = [
        threading.Thread(
            target=processor.process,
            args=(PubSubNotificationDto(email_address=ACCOUNT_ID, history_id="900"),),
        )
        for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert max_active == 1
