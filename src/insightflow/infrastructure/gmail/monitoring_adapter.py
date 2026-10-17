"""Gmail Watch + History API adapter (Phase 10).

Implements ``GmailWatchProvider`` and ``GmailHistoryProvider`` using the
same credential management as ``GoogleGmailAdapter`` — reused via
composition (``gmail_adapter.gmail_credentials()``), not duplicated. Kept
as a separate class from ``GoogleGmailAdapter`` because Watch/History is a
cohesive, independently testable capability distinct from
authentication/labels/messages; splitting here does not fragment
credential handling since both classes share the same underlying OAuth
state through the injected ``GoogleGmailAdapter``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, NoReturn

from googleapiclient.discovery import build

from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailHistoryRecordDto,
    GmailWatchResultDto,
)
from insightflow.application.exceptions.gmail import (
    GmailHistoryUnavailableError,
    GmailWatchError,
)
from insightflow.infrastructure.gmail.adapter import GoogleGmailAdapter
from insightflow.infrastructure.gmail.errors import raise_translated_google_error

logger = logging.getLogger("insightflow.infrastructure.gmail")

# labelAdded matters because a message becomes newly relevant to a
# monitored Topic when a monitored label is applied after the message
# already existed — relying only on messageAdded would miss that case.
_HISTORY_TYPES = ("messageAdded", "labelAdded")
HARD_HISTORY_PAGE_SIZE = 500


class GoogleGmailMonitoringAdapter:
    """Implements GmailWatchProvider + GmailHistoryProvider (Phase 10)."""

    def __init__(self, gmail_adapter: GoogleGmailAdapter) -> None:
        self._gmail = gmail_adapter

    def start_watch(
        self, *, label_ids: tuple[str, ...], pubsub_topic: str
    ) -> GmailWatchResultDto:
        credentials = self._gmail.gmail_credentials()
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            response = (
                service.users()
                .watch(
                    userId="me",
                    body={
                        "topicName": pubsub_topic,
                        "labelIds": list(label_ids),
                        "labelFilterBehavior": "INCLUDE",
                    },
                )
                .execute()
            )
        except Exception as exc:
            raise_translated_google_error(exc)

        is_mapping = isinstance(response, dict)
        history_id = response.get("historyId") if is_mapping else None
        expiration_ms = response.get("expiration") if is_mapping else None
        if not history_id or not expiration_ms:
            raise GmailWatchError("Gmail watch response was missing required fields.")
        expiration = datetime.fromtimestamp(int(expiration_ms) / 1000, tz=UTC)
        logger.info("Gmail watch established labels=%s", len(label_ids))
        return GmailWatchResultDto(history_id=str(history_id), expiration=expiration)

    def stop_watch(self) -> None:
        credentials = self._gmail.gmail_credentials()
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            service.users().stop(userId="me").execute()
        except Exception as exc:
            raise_translated_google_error(exc)
        logger.info("Gmail watch stopped.")

    def list_history(
        self,
        *,
        start_history_id: str,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> GmailHistoryPageDto:
        credentials = self._gmail.gmail_credentials()
        capped = max(1, min(max_results, HARD_HISTORY_PAGE_SIZE))
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            response = (
                service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=list(_HISTORY_TYPES),
                    maxResults=capped,
                    pageToken=page_token,
                )
                .execute()
            )
        except Exception as exc:
            self._raise_history_error(exc)

        entries = response.get("history", []) if isinstance(response, dict) else []
        records = _extract_records(entries)
        return GmailHistoryPageDto(
            records=records,
            next_page_token=response.get("nextPageToken"),
            history_id=response.get("historyId"),
        )

    @staticmethod
    def _raise_history_error(exc: Exception) -> NoReturn:
        status_code = getattr(exc, "status_code", None)
        resp = getattr(exc, "resp", None)
        if status_code is None and resp is not None:
            status_code = getattr(resp, "status", None)
        message = str(exc).lower()
        if status_code == 404 or "not found" in message or "invalid" in message:
            raise GmailHistoryUnavailableError(
                "The requested Gmail history position is no longer available."
            ) from exc
        raise_translated_google_error(exc)


def _extract_records(
    history_entries: list[Any],
) -> tuple[GmailHistoryRecordDto, ...]:
    records: list[GmailHistoryRecordDto] = []
    for entry in history_entries:
        if not isinstance(entry, dict):
            continue
        history_id = str(entry.get("id") or "")
        if not history_id:
            continue
        for key in ("messagesAdded", "labelsAdded"):
            for item in entry.get(key, []) or []:
                message = item.get("message") if isinstance(item, dict) else None
                record = _record_from_message(message, history_id)
                if record is not None:
                    records.append(record)
    return tuple(records)


def _record_from_message(message: Any, history_id: str) -> GmailHistoryRecordDto | None:
    if not isinstance(message, dict):
        return None
    message_id = message.get("id")
    if not message_id:
        return None
    label_ids = tuple(str(item) for item in message.get("labelIds") or [])
    return GmailHistoryRecordDto(
        message_id=str(message_id), history_id=history_id, label_ids=label_ids
    )
