"""Gmail-related application DTOs (no tokens, no Google SDK types)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GmailAccountDto:
    account_id: str
    email: str
    display_name: str | None
    provider: str = "GMAIL"


@dataclass(frozen=True, slots=True)
class GmailConnectionStatusDto:
    status: str
    account: GmailAccountDto | None = None
    last_verified_at: datetime | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class GmailLabelDto:
    label_id: str
    name: str
    label_type: str
    message_list_visibility: str | None = None
    label_list_visibility: str | None = None


@dataclass(frozen=True, slots=True)
class MapGmailLabelToTopicRequest:
    label_id: str
    topic_id: str | None = None
    topic_name: str | None = None
    topic_description: str | None = None
    label_name: str | None = None


@dataclass(frozen=True, slots=True)
class GmailLabelMappingDto:
    topic_id: str
    topic_name: str
    account_id: str
    label_id: str
    label_name: str | None
