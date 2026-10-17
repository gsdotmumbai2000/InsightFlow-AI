"""GooglePubSubAdapter tests (Phase 10) — mocked googleapiclient."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from insightflow.application.exceptions.pubsub import PubSubSubscriptionError
from insightflow.infrastructure.pubsub import adapter as adapter_module
from insightflow.infrastructure.pubsub.adapter import GooglePubSubAdapter


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


class _FakeSubscriptionsResource:
    def __init__(
        self,
        *,
        pull_response: Any = None,
        pull_exception: Exception | None = None,
        ack_exception: Exception | None = None,
    ) -> None:
        self._pull_response = pull_response
        self._pull_exception = pull_exception
        self._ack_exception = ack_exception
        self.pull_calls: list[dict[str, Any]] = []
        self.ack_calls: list[dict[str, Any]] = []

    def pull(self, **kwargs: Any) -> _Execution:
        self.pull_calls.append(kwargs)
        return _Execution(self._pull_response, self._pull_exception)

    def acknowledge(self, **kwargs: Any) -> _Execution:
        self.ack_calls.append(kwargs)
        return _Execution({}, self._ack_exception)


class _FakeProjects:
    def __init__(self, subscriptions: _FakeSubscriptionsResource) -> None:
        self._subscriptions = subscriptions

    def subscriptions(self) -> _FakeSubscriptionsResource:
        return self._subscriptions


class _FakeService:
    def __init__(self, subscriptions: _FakeSubscriptionsResource) -> None:
        self._projects = _FakeProjects(subscriptions)

    def projects(self) -> _FakeProjects:
        return self._projects


def _patch_build(monkeypatch: pytest.MonkeyPatch, service: _FakeService) -> None:
    monkeypatch.setattr(adapter_module, "build", lambda *args, **kwargs: service)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_pull_decodes_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b'{"emailAddress": "user@example.com", "historyId": "100"}'
    response = {
        "receivedMessages": [
            {
                "ackId": "ack-1",
                "message": {"data": _b64(payload), "messageId": "msg-1"},
            }
        ]
    }
    subscriptions = _FakeSubscriptionsResource(pull_response=response)
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    messages = adapter.pull(max_messages=10)

    assert len(messages) == 1
    assert messages[0].ack_id == "ack-1"
    assert messages[0].data == payload
    assert messages[0].message_id == "msg-1"
    assert subscriptions.pull_calls[0]["subscription"] == "projects/p/subscriptions/s"
    assert subscriptions.pull_calls[0]["body"]["maxMessages"] == 10


def test_pull_empty_response_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriptions = _FakeSubscriptionsResource(pull_response={})
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    assert adapter.pull(max_messages=10) == []


def test_pull_skips_malformed_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        "receivedMessages": [
            {"ackId": "ack-1", "message": {"data": "not-valid-base64!!"}},
            {"message": {"data": _b64(b"{}")}},  # missing ackId
        ]
    }
    subscriptions = _FakeSubscriptionsResource(pull_response=response)
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    assert adapter.pull(max_messages=10) == []


def test_pull_translates_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    subscriptions = _FakeSubscriptionsResource(pull_exception=RuntimeError("network"))
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    with pytest.raises(PubSubSubscriptionError):
        adapter.pull(max_messages=10)


def test_acknowledge_sends_ack_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    subscriptions = _FakeSubscriptionsResource()
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    adapter.acknowledge(("ack-1", "ack-2"))

    assert subscriptions.ack_calls[0]["body"]["ackIds"] == ["ack-1", "ack-2"]


def test_acknowledge_empty_tuple_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    subscriptions = _FakeSubscriptionsResource()
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    adapter.acknowledge(())

    assert subscriptions.ack_calls == []


def test_acknowledge_translates_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    subscriptions = _FakeSubscriptionsResource(ack_exception=RuntimeError("network"))
    _patch_build(monkeypatch, _FakeService(subscriptions))
    adapter = GooglePubSubAdapter(
        credentials=object(),  # type: ignore[arg-type]
        subscription_path="projects/p/subscriptions/s",
    )

    with pytest.raises(PubSubSubscriptionError):
        adapter.acknowledge(("ack-1",))
