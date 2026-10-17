"""Provider-neutral email/message DTOs (Phase 8: Gmail message retrieval).

These types cross the application boundary. Infrastructure adapters (Gmail)
translate provider-specific payloads into these DTOs; no Google SDK type may
appear here or in any consumer of this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from insightflow.domain.events import IntelligenceEventCreated


@dataclass(frozen=True, slots=True)
class EmailAddressDto:
    """A single parsed address (display name is optional)."""

    email: str
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class EmailAttachmentDto:
    """Attachment metadata only — never attachment bytes."""

    filename: str
    mime_type: str
    attachment_id: str | None
    size_estimate: int | None
    is_inline: bool = False
    content_id: str | None = None


@dataclass(frozen=True, slots=True)
class EmailMessageDto:
    """Provider-neutral normalized email message."""

    provider: str
    external_message_id: str
    thread_id: str | None
    subject: str | None
    sender: EmailAddressDto | None
    recipients: tuple[EmailAddressDto, ...]
    cc: tuple[EmailAddressDto, ...]
    bcc: tuple[EmailAddressDto, ...]
    reply_to: tuple[EmailAddressDto, ...]
    message_id_header: str | None
    in_reply_to: str | None
    references: tuple[str, ...]
    received_at: datetime | None
    date_header: datetime | None
    snippet: str | None
    text_body: str | None
    html_body: str | None
    label_ids: tuple[str, ...]
    attachments: tuple[EmailAttachmentDto, ...]
    size_estimate: int | None
    history_id: str | None
    content_truncated: bool = False


@dataclass(frozen=True, slots=True)
class ListGmailMessagesRequest:
    """Request one page of message references for a Gmail label."""

    label_id: str
    max_results: int = 50
    page_token: str | None = None


@dataclass(frozen=True, slots=True)
class GmailMessageRefDto:
    """A message identity returned by messages.list, before full retrieval."""

    message_id: str
    thread_id: str | None = None


@dataclass(frozen=True, slots=True)
class GmailMessageListPageDto:
    """One page of message references."""

    messages: tuple[GmailMessageRefDto, ...]
    next_page_token: str | None
    result_size_estimate: int | None = None


@dataclass(frozen=True, slots=True)
class RetrieveTopicMessagesRequest:
    """Bounded request to retrieve recent messages for a Topic's Gmail label."""

    topic_id: str
    max_messages: int = 50


@dataclass(frozen=True, slots=True)
class FailedMessageDto:
    """A message that could not be retrieved/normalized; batch continues."""

    message_id: str
    error_message: str


@dataclass(frozen=True, slots=True)
class RetrieveTopicMessagesResult:
    """Result of a bounded message retrieval for one Topic."""

    topic_id: str
    label_id: str
    requested_max_messages: int
    messages: tuple[EmailMessageDto, ...] = field(default_factory=tuple)
    failed: tuple[FailedMessageDto, ...] = field(default_factory=tuple)
    has_more: bool = False


@dataclass(frozen=True, slots=True)
class IngestTopicMessagesRequest:
    """Bounded request to retrieve and persist recent messages as events."""

    topic_id: str
    max_messages: int = 50


@dataclass(frozen=True, slots=True)
class IngestedEventDto:
    """One newly created IntelligenceEvent (Phase 9), plus what it carried."""

    event_id: str
    external_message_id: str
    attachment_count: int


@dataclass(frozen=True, slots=True)
class IngestTopicMessagesResult:
    """Result of retrieving and persisting recent messages for one Topic."""

    topic_id: str
    label_id: str
    requested_max_messages: int
    created: tuple[IngestedEventDto, ...] = field(default_factory=tuple)
    duplicate_count: int = 0
    failed: tuple[FailedMessageDto, ...] = field(default_factory=tuple)
    has_more: bool = False
    domain_events: tuple[IntelligenceEventCreated, ...] = field(default_factory=tuple)


IngestMessageStatus = Literal["CREATED", "DUPLICATE", "FAILED"]


@dataclass(frozen=True, slots=True)
class IngestMessageOutcome:
    """Outcome of mapping + persisting one already-retrieved Gmail message.

    The single shared result of ``IngestTopicMessagesUseCase.ingest_message``,
    used by both the manual/bulk retrieval path (``execute``) and Phase 10's
    real-time history-sync path — the one place Gmail -> IntelligenceEvent
    mapping, deduplication, and attachment persistence happen.
    """

    status: IngestMessageStatus
    event: IngestedEventDto | None = None
    error_message: str | None = None
    domain_event: IntelligenceEventCreated | None = None
