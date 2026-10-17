"""GoogleGmailAdapter message retrieval tests (mocked Google API, no network)."""

from __future__ import annotations

import base64
from typing import Any

import pytest

import insightflow.infrastructure.gmail.adapter as adapter_module
from insightflow.application.dto.email import ListGmailMessagesRequest
from insightflow.application.exceptions.gmail import (
    GmailMessageNotFoundError,
    GmailMessageParsingError,
)
from insightflow.configuration.models import GmailSettings
from insightflow.infrastructure.gmail.adapter import (
    GMAIL_LIST_MAX_RESULTS,
    GoogleGmailAdapter,
)
from insightflow.infrastructure.secrets.in_memory import InMemorySecretStore


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode("ascii").rstrip("=")


class _FakeExecutable:
    def __init__(self, result: Any) -> None:
        self._result = result

    def execute(self) -> Any:
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _FakeMessagesResource:
    def __init__(
        self,
        *,
        list_response: dict[str, Any] | None = None,
        get_response_by_id: dict[str, Any] | None = None,
    ) -> None:
        self._list_response = list_response or {}
        self._get_response_by_id = get_response_by_id or {}
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []

    def list(self, **kwargs: Any) -> _FakeExecutable:
        self.list_calls.append(kwargs)
        return _FakeExecutable(self._list_response)

    def get(self, **kwargs: Any) -> _FakeExecutable:
        self.get_calls.append(kwargs)
        return _FakeExecutable(self._get_response_by_id[kwargs["id"]])


class _FakeUsersResource:
    def __init__(self, messages_resource: _FakeMessagesResource) -> None:
        self._messages = messages_resource

    def messages(self) -> _FakeMessagesResource:
        return self._messages


class _FakeService:
    def __init__(self, messages_resource: _FakeMessagesResource) -> None:
        self._users = _FakeUsersResource(messages_resource)

    def users(self) -> _FakeUsersResource:
        return self._users


def _make_adapter() -> GoogleGmailAdapter:
    return GoogleGmailAdapter(
        settings=GmailSettings(
            client_id="client",
            client_secret="secret",
            client_secrets_file=None,
            oauth_local_port=0,
        ),
        secret_store=InMemorySecretStore(),
        oauth_port=0,
    )


def _patch_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        GoogleGmailAdapter, "_require_valid_credentials", lambda self: object()
    )


def _patch_service(
    monkeypatch: pytest.MonkeyPatch, messages_resource: _FakeMessagesResource
) -> None:
    monkeypatch.setattr(
        adapter_module, "build", lambda *args, **kwargs: _FakeService(messages_resource)
    )


def test_list_message_ids_filters_by_label_and_returns_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_credentials(monkeypatch)
    resource = _FakeMessagesResource(
        list_response={
            "messages": [
                {"id": "m1", "threadId": "t1"},
                {"id": "m2", "threadId": "t2"},
            ],
            "nextPageToken": "TOKEN2",
            "resultSizeEstimate": 10,
        }
    )
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    page = adapter.list_message_ids(
        ListGmailMessagesRequest(label_id="Label_1", max_results=5)
    )

    assert [ref.message_id for ref in page.messages] == ["m1", "m2"]
    assert page.next_page_token == "TOKEN2"
    assert page.result_size_estimate == 10
    call = resource.list_calls[0]
    assert call["labelIds"] == ["Label_1"]
    assert call["userId"] == "me"
    assert call["maxResults"] == 5


def test_list_message_ids_caps_max_results_at_gmail_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_credentials(monkeypatch)
    resource = _FakeMessagesResource(list_response={"messages": []})
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    adapter.list_message_ids(
        ListGmailMessagesRequest(label_id="Label_1", max_results=999_999)
    )

    assert resource.list_calls[0]["maxResults"] == GMAIL_LIST_MAX_RESULTS


def test_list_message_ids_passes_page_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_credentials(monkeypatch)
    resource = _FakeMessagesResource(list_response={"messages": []})
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    adapter.list_message_ids(
        ListGmailMessagesRequest(label_id="Label_1", max_results=10, page_token="ABC")
    )

    assert resource.list_calls[0]["pageToken"] == "ABC"


def test_get_message_returns_normalized_dto(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_credentials(monkeypatch)
    raw = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX"],
        "snippet": "s",
        "internalDate": "1690000000000",
        "sizeEstimate": 10,
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "Subject", "value": "Hi"}],
            "body": {"data": _b64("Body"), "size": 4},
        },
    }
    resource = _FakeMessagesResource(get_response_by_id={"m1": raw})
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    dto = adapter.get_message("m1")

    assert dto.subject == "Hi"
    assert dto.text_body == "Body"
    assert dto.external_message_id == "m1"
    call = resource.get_calls[0]
    assert call["id"] == "m1"
    assert call["format"] == "full"
    assert call["userId"] == "me"


def test_get_message_translates_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_credentials(monkeypatch)

    class _NotFoundError(Exception):
        status_code = 404

    resource = _FakeMessagesResource(
        get_response_by_id={"missing": _NotFoundError("not found")}
    )
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    with pytest.raises(GmailMessageNotFoundError):
        adapter.get_message("missing")


def test_get_message_wraps_parsing_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_credentials(monkeypatch)
    raw = {
        "id": "m1",
        "payload": {
            "mimeType": "text/plain",
            "headers": [],
            "body": {"data": "###not-valid###", "size": 1},
        },
    }
    resource = _FakeMessagesResource(get_response_by_id={"m1": raw})
    _patch_service(monkeypatch, resource)

    adapter = _make_adapter()
    with pytest.raises(GmailMessageParsingError):
        adapter.get_message("m1")
