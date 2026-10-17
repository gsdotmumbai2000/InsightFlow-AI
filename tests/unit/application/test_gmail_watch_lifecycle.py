"""GmailWatchLifecycleService tests (Phase 10) — fakes only, no network."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest
from insightflow.application.exceptions.monitoring import MonitoringConfigurationError
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)
from insightflow.application.use_cases import ApplicationUseCases


def _build_service(
    store: InMemoryStore,
    gmail: FakeGmailAdapter,
    *,
    project_id: str | None = "test-project",
    topic_name: str | None = "gmail-topic",
    subscription: str | None = "gmail-sub",
) -> GmailWatchLifecycleService:
    return GmailWatchLifecycleService(
        store.unit_of_work_factory,
        gmail,
        pubsub_project_id=project_id,
        pubsub_topic_name=topic_name,
        pubsub_subscription=subscription,
    )


def test_establish_watch_creates_state(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.watch_history_id = "555"
    service = _build_service(store, gmail)

    state = service.establish_watch(account_id="user@example.com")

    assert state.current_history_id == "555"
    assert state.pubsub_project_id == "test-project"
    assert len(gmail.watch_calls) == 1
    label_ids, topic_resource = gmail.watch_calls[0]
    assert label_ids == ("Label_A",)
    assert topic_resource == "projects/test-project/topics/gmail-topic"


def test_establish_watch_updates_existing_state(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    service = _build_service(store, gmail)
    first = service.establish_watch(account_id="user@example.com")

    gmail.watch_history_id = "999"
    second = service.establish_watch(account_id="user@example.com")

    assert first.id.value == second.id.value
    assert second.current_history_id == "999"
    assert len(gmail.watch_calls) == 2


def test_establish_watch_missing_pubsub_config_raises(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    service = _build_service(store, gmail, topic_name=None)
    with pytest.raises(MonitoringConfigurationError):
        service.establish_watch(account_id="user@example.com")


def test_establish_watch_no_monitored_topics_raises(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    service = _build_service(store, gmail)
    with pytest.raises(MonitoringConfigurationError):
        service.establish_watch(account_id="user@example.com")


def test_topic_mapping_change_reflected_in_next_watch_call(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    service = _build_service(store, gmail)
    service.establish_watch(account_id="user@example.com")
    assert gmail.watch_calls[-1][0] == ("Label_A",)

    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_B", topic_name="MODI")
    )
    service.establish_watch(account_id="user@example.com")
    assert set(gmail.watch_calls[-1][0]) == {"Label_A", "Label_B"}


def test_stop_watch_marks_stopped_and_calls_provider(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    service = _build_service(store, gmail)
    service.establish_watch(account_id="user@example.com")

    state = service.stop_watch(account_id="user@example.com")

    assert state is not None
    assert state.status.value == "STOPPED"
    assert gmail.stop_watch_calls == 1


def test_stop_watch_missing_state_returns_none(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    service = _build_service(store, gmail)
    assert service.stop_watch(account_id="nobody@example.com") is None


def test_renew_if_needed_skips_when_not_due(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.watch_expiration = datetime.now(UTC) + timedelta(days=6)
    service = _build_service(store, gmail)
    state = service.establish_watch(account_id="user@example.com")
    state.mark_running()
    with store.unit_of_work_factory() as uow:
        uow.monitoring_states.update(state)
        uow.commit()
    calls_before = len(gmail.watch_calls)

    result = service.renew_if_needed(account_id="user@example.com", margin_hours=24)

    assert result is not None
    assert len(gmail.watch_calls) == calls_before


def test_renew_if_needed_renews_when_due(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.watch_expiration = datetime.now(UTC) + timedelta(hours=1)
    service = _build_service(store, gmail)
    state = service.establish_watch(account_id="user@example.com")
    state.mark_running()
    with store.unit_of_work_factory() as uow:
        uow.monitoring_states.update(state)
        uow.commit()
    calls_before = len(gmail.watch_calls)

    result = service.renew_if_needed(account_id="user@example.com", margin_hours=24)

    assert result is not None
    assert len(gmail.watch_calls) == calls_before + 1


def test_renew_if_needed_no_state_returns_none(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    service = _build_service(store, gmail)
    result = service.renew_if_needed(account_id="nobody@example.com", margin_hours=24)
    assert result is None


def test_renew_if_needed_inactive_state_is_not_renewed(
    use_cases: ApplicationUseCases, gmail: FakeGmailAdapter, store: InMemoryStore
) -> None:
    gmail.connect()
    use_cases.map_gmail_label_to_topic.execute(
        MapGmailLabelToTopicRequest(label_id="Label_A", topic_name="TRUMP")
    )
    gmail.watch_expiration = datetime.now(UTC) + timedelta(hours=1)
    service = _build_service(store, gmail)
    state = service.establish_watch(account_id="user@example.com")
    state.mark_stopped()
    with store.unit_of_work_factory() as uow:
        uow.monitoring_states.update(state)
        uow.commit()
    calls_before = len(gmail.watch_calls)

    service.renew_if_needed(account_id="user@example.com", margin_hours=24)

    assert len(gmail.watch_calls) == calls_before


def test_pubsub_topic_resource_none_when_unconfigured(
    store: InMemoryStore, gmail: FakeGmailAdapter
) -> None:
    service = _build_service(store, gmail, topic_name=None)
    assert service.pubsub_topic_resource is None
