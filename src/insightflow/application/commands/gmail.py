"""Gmail application use cases."""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Protocol, runtime_checkable
from uuid import uuid4

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.commands.events import CreateIntelligenceEventUseCase
from insightflow.application.dto.email import (
    EmailMessageDto,
    FailedMessageDto,
    GmailMessageRefDto,
    IngestedEventDto,
    IngestMessageOutcome,
    IngestTopicMessagesRequest,
    IngestTopicMessagesResult,
    ListGmailMessagesRequest,
    RetrieveTopicMessagesRequest,
    RetrieveTopicMessagesResult,
)
from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
    GmailLabelMappingDto,
    MapGmailLabelToTopicRequest,
)
from insightflow.application.dto.mappers import topic_to_dto
from insightflow.application.dto.models import CreateIntelligenceEventRequest, TopicDto
from insightflow.application.exceptions import (
    ApplicationError,
    ApplicationValidationError,
    DuplicateEventError,
    DuplicateTopicError,
    TopicNotFoundError,
)
from insightflow.application.exceptions.gmail import (
    GmailConnectionError,
    GmailError,
    TopicNotGmailConfiguredError,
)
from insightflow.application.ports.gmail import (
    GmailAuthenticator,
    GmailLabelProvider,
    GmailMessageProvider,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    Attachment,
    EventId,
    IntelligenceEventCreated,
    SourceConfiguration,
    SourceType,
    Topic,
    TopicId,
)

logger = logging.getLogger("insightflow.application.gmail")

# Bounded retrieval: callers may request fewer, but never more than this,
# regardless of input, to avoid an accidental unbounded mailbox download.
HARD_MAX_MESSAGES = 500


@runtime_checkable
class _MonitoringWorkerHandle(Protocol):
    """Structural stand-in for MonitoringWorkerHandle (Phase 10).

    Avoids importing the concrete class: application/services/* imports
    back into this module (e.g. gmail_full_sync -> IngestTopicMessagesUseCase),
    so importing MonitoringWorkerHandle here directly would be circular.
    """

    @property
    def is_running(self) -> bool: ...
    def stop(self) -> None: ...


class ConnectGmailUseCase:
    def __init__(self, authenticator: GmailAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> GmailAccountDto:
        with use_case_scope("ConnectGmail"):
            return self._authenticator.connect()


class DisconnectGmailUseCase:
    """Disconnect Gmail; also safely stops real-time monitoring if active.

    Per Phase 10: a running monitoring worker must not continue against an
    account whose credentials are about to be removed. Stopping the worker
    is best-effort and never blocks/aborts the disconnect itself — the
    Gmail-side watch subscription simply expires on its own if it cannot
    be explicitly cancelled here.
    """

    def __init__(
        self,
        authenticator: GmailAuthenticator,
        monitoring_worker_handle: _MonitoringWorkerHandle | None = None,
    ) -> None:
        self._authenticator = authenticator
        self._monitoring_worker_handle = monitoring_worker_handle

    def execute(self) -> None:
        with use_case_scope("DisconnectGmail"):
            if (
                self._monitoring_worker_handle is not None
                and self._monitoring_worker_handle.is_running
            ):
                logger.info("Stopping real-time monitoring before Gmail disconnect.")
                self._monitoring_worker_handle.stop()
            self._authenticator.disconnect()


class GetGmailConnectionStatusUseCase:
    def __init__(self, authenticator: GmailAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> GmailConnectionStatusDto:
        with use_case_scope("GetGmailConnectionStatus"):
            return self._authenticator.get_connection_status()


class ListGmailLabelsUseCase:
    def __init__(
        self,
        authenticator: GmailAuthenticator,
        labels: GmailLabelProvider,
    ) -> None:
        self._authenticator = authenticator
        self._labels = labels

    def execute(self) -> list[GmailLabelDto]:
        with use_case_scope("ListGmailLabels"):
            status = self._authenticator.get_connection_status()
            if status.status != "CONNECTED":
                raise GmailConnectionError(
                    status.message or "Gmail must be connected to list labels."
                )
            return self._labels.list_labels()


class MapGmailLabelToTopicUseCase:
    """Associate a Gmail label with a Topic via SourceConfiguration."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        authenticator: GmailAuthenticator,
    ) -> None:
        self._uow_factory = uow_factory
        self._authenticator = authenticator

    def execute(self, request: MapGmailLabelToTopicRequest) -> GmailLabelMappingDto:
        with use_case_scope("MapGmailLabelToTopic"):

            def _run() -> GmailLabelMappingDto:
                account = self._authenticator.get_account()
                if account is None:
                    raise GmailConnectionError("Gmail is not connected.")
                label_id = request.label_id.strip()
                if not label_id:
                    raise ApplicationValidationError("label_id must not be empty")

                source = SourceConfiguration(
                    source_type=SourceType.GMAIL,
                    source_id=account.account_id,
                    source_identifier=label_id,
                )
                with unit_of_work_scope(self._uow_factory) as uow:
                    existing = uow.topics.find_by_source_identifier(
                        source_id=source.source_id,
                        source_identifier=source.source_identifier,
                    )
                    if request.topic_id:
                        if (
                            existing is not None
                            and existing.id.value != request.topic_id
                        ):
                            raise DuplicateTopicError(
                                "Another topic already uses this Gmail label."
                            )
                        topic = uow.topics.get(TopicId(request.topic_id))
                        if topic is None:
                            raise TopicNotFoundError(
                                f"Topic not found: {request.topic_id}"
                            )
                        topic.source_configuration = source
                        if request.label_name:
                            topic.metadata["gmail_label_name"] = request.label_name
                        topic.updated_at = datetime.now(UTC)
                        uow.topics.update(topic)
                    else:
                        if existing is not None:
                            raise DuplicateTopicError(
                                "A topic already exists for this Gmail label."
                            )
                        name = (request.topic_name or "").strip()
                        if not name:
                            raise ApplicationValidationError(
                                "topic_name is required when creating a topic"
                            )
                        topic = Topic.create(
                            name=name,
                            source_configuration=source,
                            description=request.topic_description,
                        )
                        if request.label_name:
                            topic.metadata["gmail_label_name"] = request.label_name
                        uow.topics.add(topic)
                    uow.commit()
                    return GmailLabelMappingDto(
                        topic_id=topic.id.value,
                        topic_name=topic.name,
                        account_id=account.account_id,
                        label_id=label_id,
                        label_name=request.label_name,
                    )

            return run_mutating(_run)


class RemoveGmailLabelMappingUseCase:
    """Clear Gmail source binding from a topic (reverts to local GENERIC source)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        with use_case_scope("RemoveGmailLabelMapping"):

            def _run() -> TopicDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    topic = uow.topics.get(TopicId(topic_id))
                    if topic is None:
                        raise TopicNotFoundError(f"Topic not found: {topic_id}")
                    topic.source_configuration = SourceConfiguration(
                        source_type=SourceType.GENERIC,
                        source_id="local",
                        source_identifier=f"manual-{uuid4()}",
                    )
                    topic.metadata.pop("gmail_label_name", None)
                    topic.updated_at = datetime.now(UTC)
                    uow.topics.update(topic)
                    uow.commit()
                    return topic_to_dto(topic)

            return run_mutating(_run)


class RetrieveTopicMessagesUseCase:
    """Retrieve a bounded number of recent Gmail messages for a Topic.

    Foundation for Phase 9+ processing: normalizes provider messages and
    returns them without creating any IntelligenceEvent records.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        authenticator: GmailAuthenticator,
        messages: GmailMessageProvider,
    ) -> None:
        self._uow_factory = uow_factory
        self._authenticator = authenticator
        self._messages = messages

    def execute(
        self, request: RetrieveTopicMessagesRequest
    ) -> RetrieveTopicMessagesResult:
        with use_case_scope("RetrieveTopicMessages"):
            max_messages = max(1, min(request.max_messages, HARD_MAX_MESSAGES))

            with unit_of_work_scope(self._uow_factory) as uow:
                topic = uow.topics.get(TopicId(request.topic_id))
            if topic is None:
                raise TopicNotFoundError(f"Topic not found: {request.topic_id}")
            if topic.source_configuration.source_type is not SourceType.GMAIL:
                raise TopicNotGmailConfiguredError(
                    f"Topic '{topic.name}' has no Gmail label configured."
                )
            account = self._authenticator.get_account()
            if account is None:
                raise GmailConnectionError(
                    "Gmail is not connected. Connect Gmail before retrieving messages."
                )

            label_id = topic.source_configuration.source_identifier
            started = time.monotonic()
            refs = self._collect_message_refs(label_id, max_messages)
            has_more = len(refs) > max_messages
            refs = refs[:max_messages]

            emails: list[EmailMessageDto] = []
            failed: list[FailedMessageDto] = []
            for ref in refs:
                try:
                    emails.append(self._messages.get_message(ref.message_id))
                except GmailError as exc:
                    logger.warning(
                        "Gmail message retrieval failed message_id=%s error=%s",
                        ref.message_id,
                        type(exc).__name__,
                    )
                    failed.append(
                        FailedMessageDto(
                            message_id=ref.message_id, error_message=str(exc)
                        )
                    )

            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Retrieved Gmail messages topic_id=%s label_id=%s requested=%s "
                "retrieved=%s failed=%s elapsed_ms=%s",
                topic.id.value,
                label_id,
                max_messages,
                len(emails),
                len(failed),
                elapsed_ms,
            )
            return RetrieveTopicMessagesResult(
                topic_id=topic.id.value,
                label_id=label_id,
                requested_max_messages=max_messages,
                messages=tuple(emails),
                failed=tuple(failed),
                has_more=has_more,
            )

    def _collect_message_refs(
        self, label_id: str, max_messages: int
    ) -> list[GmailMessageRefDto]:
        """Page through messages.list until bounded or exhausted."""
        refs: list[GmailMessageRefDto] = []
        page_token: str | None = None
        while len(refs) <= max_messages:
            page = self._messages.list_message_ids(
                ListGmailMessagesRequest(
                    label_id=label_id,
                    max_results=max_messages - len(refs) + 1,
                    page_token=page_token,
                )
            )
            refs.extend(page.messages)
            page_token = page.next_page_token
            if page_token is None or not page.messages:
                break
        return refs


class _HtmlTextExtractor(HTMLParser):
    """Minimal, dependency-free HTML-to-text conversion for untrusted mail."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self.chunks.append(data.strip())


def _strip_html(html_content: str) -> str:
    """Best-effort plain text from untrusted HTML; never raises."""
    extractor = _HtmlTextExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        return ""
    return " ".join(extractor.chunks)


def _normalize_content(message: EmailMessageDto) -> str | None:
    """Prefer plain text; fall back to a light HTML-derived text extraction."""
    if message.text_body and message.text_body.strip():
        return message.text_body.strip()
    if message.html_body and message.html_body.strip():
        return _strip_html(message.html_body) or None
    return None


def _compute_content_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _gmail_permalink(message_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{message_id}"


def _email_message_to_create_event_request(
    message: EmailMessageDto, *, topic_id: str, account_id: str
) -> CreateIntelligenceEventRequest:
    """Normalize a Gmail message (Phase 8) into the generic event contract.

    ``received_at`` is deliberately left unset so ``IntelligenceEvent.create``
    defaults it to ingestion time — distinct from ``source_published_at``
    (Gmail's own internalDate-derived timestamp).
    """
    normalized_content = _normalize_content(message)
    return CreateIntelligenceEventRequest(
        source_type=SourceType.GMAIL.value,
        source_id=account_id,
        external_id=message.external_message_id,
        topic_id=topic_id,
        thread_id=message.thread_id,
        account_id=account_id,
        url=_gmail_permalink(message.external_message_id),
        title=message.subject,
        normalized_content=normalized_content,
        source_published_at=message.received_at,
        content_hash=_compute_content_hash(normalized_content),
    )


class IngestTopicMessagesUseCase:
    """Retrieve recent Gmail messages for a Topic and persist them as events.

    Composes existing use cases rather than reimplementing them:
    ``RetrieveTopicMessagesUseCase`` (Phase 8 normalization/pagination) and
    ``CreateIntelligenceEventUseCase`` (Phase 5 creation + idempotent
    deduplication via source_id+external_id). This use case owns only the
    Gmail -> IntelligenceEvent field mapping and attachment-metadata
    persistence.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        retrieve: RetrieveTopicMessagesUseCase,
        create_event: CreateIntelligenceEventUseCase,
        *,
        on_event_created: Callable[[IntelligenceEventCreated], None] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._retrieve = retrieve
        self._create_event = create_event
        self._on_event_created = on_event_created

    def execute(self, request: IngestTopicMessagesRequest) -> IngestTopicMessagesResult:
        with use_case_scope("IngestTopicMessages"):
            with unit_of_work_scope(self._uow_factory) as uow:
                topic = uow.topics.get(TopicId(request.topic_id))
            if topic is None:
                raise TopicNotFoundError(f"Topic not found: {request.topic_id}")
            account_id = topic.source_configuration.source_id

            retrieval = self._retrieve.execute(
                RetrieveTopicMessagesRequest(
                    topic_id=request.topic_id, max_messages=request.max_messages
                )
            )

            created: list[IngestedEventDto] = []
            duplicate_count = 0
            failed: list[FailedMessageDto] = list(retrieval.failed)
            domain_events: list[IntelligenceEventCreated] = []
            started = time.monotonic()

            for message in retrieval.messages:
                outcome = self.ingest_message(
                    message, topic_id=retrieval.topic_id, account_id=account_id
                )
                if outcome.status == "DUPLICATE":
                    duplicate_count += 1
                elif outcome.status == "FAILED":
                    failed.append(
                        FailedMessageDto(
                            message_id=message.external_message_id,
                            error_message=outcome.error_message or "",
                        )
                    )
                else:
                    assert outcome.event is not None
                    created.append(outcome.event)
                    if outcome.domain_event is not None:
                        domain_events.append(outcome.domain_event)

            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Ingested Gmail messages topic_id=%s label_id=%s requested=%s "
                "created=%s duplicate=%s failed=%s elapsed_ms=%s",
                retrieval.topic_id,
                retrieval.label_id,
                retrieval.requested_max_messages,
                len(created),
                duplicate_count,
                len(failed),
                elapsed_ms,
            )
            return IngestTopicMessagesResult(
                topic_id=retrieval.topic_id,
                label_id=retrieval.label_id,
                requested_max_messages=retrieval.requested_max_messages,
                created=tuple(created),
                duplicate_count=duplicate_count,
                failed=tuple(failed),
                has_more=retrieval.has_more,
                domain_events=tuple(domain_events),
            )

    def ingest_message(
        self, message: EmailMessageDto, *, topic_id: str, account_id: str
    ) -> IngestMessageOutcome:
        """Map + persist one already-retrieved Gmail message as an event.

        The single boundary shared by the manual/bulk retrieval path
        (``execute``, above) and Phase 10's real-time history-sync path.
        Neither path re-implements EmailMessageDto mapping, content-hash
        calculation, event creation, deduplication, or attachment
        persistence — both call this method.
        """
        create_request = _email_message_to_create_event_request(
            message, topic_id=topic_id, account_id=account_id
        )
        try:
            event_dto = self._create_event.execute(create_request)
        except DuplicateEventError:
            return IngestMessageOutcome(status="DUPLICATE")
        except ApplicationError as exc:
            logger.warning(
                "Gmail event creation failed message_id=%s error=%s",
                message.external_message_id,
                type(exc).__name__,
            )
            return IngestMessageOutcome(status="FAILED", error_message=str(exc))

        attachment_count = self._persist_attachments(event_dto.id, message)
        ingested = IngestedEventDto(
            event_id=event_dto.id,
            external_message_id=message.external_message_id,
            attachment_count=attachment_count,
        )
        domain_event = IntelligenceEventCreated(
            event_id=EventId(event_dto.id),
            topic_id=TopicId(topic_id),
            occurred_at=datetime.now(UTC),
        )
        if self._on_event_created is not None:
            self._on_event_created(domain_event)
        return IngestMessageOutcome(
            status="CREATED", event=ingested, domain_event=domain_event
        )

    def _persist_attachments(self, event_id: str, message: EmailMessageDto) -> int:
        """Persist metadata for non-inline attachments; never downloads bytes."""
        real_attachments = [a for a in message.attachments if not a.is_inline]
        if not real_attachments:
            return 0
        with unit_of_work_scope(self._uow_factory) as uow:
            for attachment_dto in real_attachments:
                attachment = Attachment.create(
                    event_id=EventId(event_id),
                    filename=attachment_dto.filename,
                    content_type=attachment_dto.mime_type,
                    size_bytes=attachment_dto.size_estimate,
                    external_id=attachment_dto.attachment_id,
                )
                uow.attachments.add(attachment)
            uow.commit()
        return len(real_attachments)
