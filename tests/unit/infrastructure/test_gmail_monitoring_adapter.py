"""GoogleGmailMonitoringAdapter tests (Phase 10) — mocked googleapiclient."""

from __future__ import annotations

from typing import Any

import pytest

from insightflow.application.exceptions.gmail import (
    GmailHistoryUnavailableError,
    GmailWatchError,
)
from insightflow.infrastructure.gmail import (
    monitoring_adapter as monitoring_adapter_module,
)
from insightflow.infrastructure.gmail.monitoring_adapter import (
    GoogleGmailMonitoringAdapter,
)


class _Execution:
    def __init__(
        self, response: Any = None, exception: Exception | None = None
    ) -> None:
        self._response = response
        self._exception = exception

    def execute(self) -> Any:
        if self._exception is not None:
            raise self._exception
        return self._response


class _FakeHistoryResource:
    def __init__(
        self, response: Any = None, exception: Exception | None = None
    ) -> None:
        self._response = response
        self._exception = exception
        self.list_calls: list[dict[str, Any]] = []

    def list(self, **kwargs: Any) -> _Execution:
        self.list_calls.append(kwargs)
        return _Execution(self._response, self._exception)


class _FakeUsersResource:
    def __init__(
        self,
        *,
        watch_response: Any = None,
        watch_exception: Exception | None = None,
        history: _FakeHistoryResource | None = None,
    ) -> None:
        self._watch_response = watch_response
        self._watch_exception = watch_exception
        self._history = history or _FakeHistoryResource()
        self.watch_calls: list[dict[str, Any]] = []
        self.stop_calls = 0

    def watch(self, **kwargs: Any) -> _Execution:
        self.watch_calls.append(kwargs)
        return _Execution(self._watch_response, self._watch_exception)

    def stop(self, **_kwargs: Any) -> _Execution:
        self.stop_calls += 1
        return _Execution({}, None)

    def history(self) -> _FakeHistoryResource:
        return self._history


class _FakeService:
    def __init__(self, users: _FakeUsersResource) -> None:
        self._users = users

    def users(self) -> _FakeUsersResource:
        return self._users


class _FakeGmailCredentialsProvider:
    def gmail_credentials(self) -> object:
        return object()


def _patch_build(monkeypatch: pytest.MonkeyPatch, service: _FakeService) -> None:
    monkeypatch.setattr(
        monitoring_adapter_module, "build", lambda *args, **kwargs: service
    )


def test_start_watch_request_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersResource(
        watch_response={"historyId": "1000", "expiration": "1999999999000"}
    )
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    adapter.start_watch(
        label_ids=("Label_A", "Label_B"), pubsub_topic="projects/p/topics/t"
    )

    assert len(users.watch_calls) == 1
    body = users.watch_calls[0]["body"]
    assert body["topicName"] == "projects/p/topics/t"
    assert body["labelIds"] == ["Label_A", "Label_B"]
    assert body["labelFilterBehavior"] == "INCLUDE"


def test_start_watch_response_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersResource(
        watch_response={"historyId": "12345", "expiration": "1893456000000"}
    )
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    result = adapter.start_watch(
        label_ids=("Label_A",), pubsub_topic="projects/p/topics/t"
    )

    assert result.history_id == "12345"
    assert result.expiration.timestamp() * 1000 == pytest.approx(
        1893456000000, rel=1e-6
    )


def test_start_watch_missing_fields_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersResource(watch_response={})
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    with pytest.raises(GmailWatchError):
        adapter.start_watch(label_ids=("Label_A",), pubsub_topic="projects/p/topics/t")


def test_stop_watch_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersResource()
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    adapter.stop_watch()

    assert users.stop_calls == 1


def test_list_history_request_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    history = _FakeHistoryResource(response={"history": [], "historyId": "200"})
    users = _FakeUsersResource(history=history)
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    adapter.list_history(start_history_id="100", page_token="tok", max_results=25)

    assert len(history.list_calls) == 1
    call = history.list_calls[0]
    assert call["startHistoryId"] == "100"
    assert call["pageToken"] == "tok"
    assert call["maxResults"] == 25
    assert set(call["historyTypes"]) == {"messageAdded", "labelAdded"}


def test_list_history_caps_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    history = _FakeHistoryResource(response={"history": []})
    users = _FakeUsersResource(history=history)
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    adapter.list_history(start_history_id="100", max_results=10_000)

    assert history.list_calls[0]["maxResults"] == 500


def test_list_history_extracts_messages_added_and_labels_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "history": [
            {
                "id": "150",
                "messagesAdded": [
                    {"message": {"id": "m1", "labelIds": ["INBOX", "TRUMP"]}}
                ],
            },
            {
                "id": "160",
                "labelsAdded": [
                    {
                        "message": {"id": "m2", "labelIds": ["INBOX", "TRUMP"]},
                        "labelIds": ["TRUMP"],
                    }
                ],
            },
        ],
        "nextPageToken": "next-token",
        "historyId": "999",
    }
    history = _FakeHistoryResource(response=response)
    users = _FakeUsersResource(history=history)
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    page = adapter.list_history(start_history_id="100")

    assert page.next_page_token == "next-token"
    assert page.history_id == "999"
    by_id = {record.message_id: record for record in page.records}
    assert set(by_id) == {"m1", "m2"}
    assert by_id["m1"].history_id == "150"
    assert by_id["m2"].history_id == "160"
    assert by_id["m2"].label_ids == ("INBOX", "TRUMP")


def test_list_history_404_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HttpError(Exception):
        status_code = 404

    history = _FakeHistoryResource(exception=_HttpError("not found"))
    users = _FakeUsersResource(history=history)
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    with pytest.raises(GmailHistoryUnavailableError):
        adapter.list_history(start_history_id="999999")


def test_list_history_deletion_only_entries_produce_no_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "history": [{"id": "150", "messagesDeleted": [{"message": {"id": "m1"}}]}],
        "historyId": "150",
    }
    history = _FakeHistoryResource(response=response)
    users = _FakeUsersResource(history=history)
    _patch_build(monkeypatch, _FakeService(users))
    adapter = GoogleGmailMonitoringAdapter(_FakeGmailCredentialsProvider())  # type: ignore[arg-type]

    page = adapter.list_history(start_history_id="100")

    assert page.records == ()
