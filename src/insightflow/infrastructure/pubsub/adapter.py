"""Google Cloud Pub/Sub subscriber adapter (REST, Phase 10).

Uses the existing ``google-api-python-client`` dependency (already used
for Gmail) rather than adding the heavier ``google-cloud-pubsub`` gRPC
package — the Pub/Sub REST API's ``projects.subscriptions.pull``/
``acknowledge`` methods provide everything the desktop subscriber needs,
authenticated with the same style of OAuth ``Credentials`` object already
used throughout this project.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from insightflow.application.dto.monitoring import PubSubMessageDto
from insightflow.application.exceptions.pubsub import PubSubSubscriptionError

logger = logging.getLogger("insightflow.infrastructure.pubsub")


class GooglePubSubAdapter:
    """Implements ``PubSubSubscriber`` against one dedicated subscription."""

    def __init__(self, *, credentials: Credentials, subscription_path: str) -> None:
        self._credentials = credentials
        self._subscription_path = subscription_path

    def pull(self, *, max_messages: int) -> list[PubSubMessageDto]:
        try:
            service = build(
                "pubsub", "v1", credentials=self._credentials, cache_discovery=False
            )
            response = (
                service.projects()
                .subscriptions()
                .pull(
                    subscription=self._subscription_path,
                    body={"maxMessages": max(1, max_messages)},
                )
                .execute()
            )
        except Exception as exc:
            raise PubSubSubscriptionError(f"Pub/Sub pull failed: {exc}") from exc

        received = (
            response.get("receivedMessages", []) if isinstance(response, dict) else []
        )
        return [item for item in (_to_message_dto(entry) for entry in received) if item]

    def acknowledge(self, ack_ids: tuple[str, ...]) -> None:
        if not ack_ids:
            return
        try:
            service = build(
                "pubsub", "v1", credentials=self._credentials, cache_discovery=False
            )
            service.projects().subscriptions().acknowledge(
                subscription=self._subscription_path,
                body={"ackIds": list(ack_ids)},
            ).execute()
        except Exception as exc:
            raise PubSubSubscriptionError(f"Pub/Sub acknowledge failed: {exc}") from exc


def _to_message_dto(entry: Any) -> PubSubMessageDto | None:
    if not isinstance(entry, dict):
        return None
    ack_id = entry.get("ackId")
    message = entry.get("message") or {}
    data_b64 = message.get("data") if isinstance(message, dict) else None
    if not ack_id or not data_b64:
        return None
    try:
        data = base64.b64decode(data_b64)
    except (ValueError, TypeError):
        logger.warning("Pub/Sub message had undecodable base64 data; skipping.")
        return None
    return PubSubMessageDto(
        ack_id=str(ack_id),
        data=data,
        message_id=message.get("messageId") if isinstance(message, dict) else None,
    )
