"""Parse Gmail Pub/Sub notification payloads (Phase 10).

The Pub/Sub message data is a small JSON envelope Gmail publishes on
mailbox change: ``{"emailAddress": "...", "historyId": "..."}``. This is a
change *signal* — never the email itself, never subject/sender/body.
"""

from __future__ import annotations

import json
import logging

from insightflow.application.dto.monitoring import PubSubNotificationDto

logger = logging.getLogger("insightflow.infrastructure.pubsub")


def parse_gmail_pubsub_notification(data: bytes) -> PubSubNotificationDto | None:
    """Return the parsed notification, or ``None`` if the payload is malformed."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Malformed Gmail Pub/Sub notification payload.")
        return None
    if not isinstance(payload, dict):
        return None
    email_address = payload.get("emailAddress")
    history_id = payload.get("historyId")
    if not email_address or not history_id:
        return None
    return PubSubNotificationDto(
        email_address=str(email_address), history_id=str(history_id)
    )
