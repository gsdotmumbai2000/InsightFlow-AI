"""Gmail mailbox-history synchronization (Phase 10).

Given a stored history cursor, retrieves only the mailbox changes since
that point (``GmailHistoryProvider``), filters to messages relevant to
currently monitored Gmail labels/Topics, and ingests each relevant message
through the existing Phase 9 ingestion boundary
(``IngestTopicMessagesUseCase.ingest_message``). No second MIME parser, no
second event-creation path.

The stored cursor must never advance past a point that was not actually
processed: a bounded-batch stop leaves the cursor at the last history
record that was durably ingested/deduplicated, not at the mailbox's
current tip.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from insightflow.application._support import unit_of_work_scope
from insightflow.application.commands.gmail import IngestTopicMessagesUseCase
from insightflow.application.dto.monitoring import HistorySyncOutcome
from insightflow.application.exceptions.gmail import GmailError
from insightflow.application.ports.gmail import (
    GmailHistoryProvider,
    GmailMessageProvider,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.services.monitored_labels import (
    monitored_label_topic_map,
)
from insightflow.domain import IntelligenceEventCreated

logger = logging.getLogger("insightflow.application.monitoring")

# Bounded per sync() call, mirroring Phase 8's message-retrieval safety
# limits — a burst of mailbox changes must not trigger an unbounded
# processing operation. A caller may call sync() again to make further
# progress; each call durably advances the stored cursor.
DEFAULT_HISTORY_BATCH_SIZE = 50
DEFAULT_HISTORY_PAGE_SIZE = 100
HARD_HISTORY_PAGE_SIZE = 500


class GmailHistorySyncService:
    """Synchronizes one Gmail account's mailbox history into IntelligenceEvents."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        history: GmailHistoryProvider,
        messages: GmailMessageProvider,
        ingest: IngestTopicMessagesUseCase,
        *,
        batch_size: int = DEFAULT_HISTORY_BATCH_SIZE,
        page_size: int = DEFAULT_HISTORY_PAGE_SIZE,
        on_event_created: Callable[[IntelligenceEventCreated], None] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._history = history
        self._messages = messages
        self._ingest = ingest
        self._batch_size = max(1, batch_size)
        self._page_size = max(1, min(page_size, HARD_HISTORY_PAGE_SIZE))
        self._on_event_created = on_event_created

    def sync(self, *, account_id: str, start_history_id: str) -> HistorySyncOutcome:
        """Synchronize mailbox changes since ``start_history_id``.

        Propagates ``GmailHistoryUnavailableError`` when the position is
        no longer valid (Gmail 404) — the caller is responsible for
        triggering full-sync recovery; this service does not retry.
        """
        candidates, final_history_id, truncated = self._collect_candidates(
            start_history_id
        )
        if not candidates:
            return HistorySyncOutcome(
                new_history_id=final_history_id or start_history_id
            )

        with unit_of_work_scope(self._uow_factory) as uow:
            label_topic_map = monitored_label_topic_map(uow)

        created = duplicate = failed = processed = 0
        last_history_id = start_history_id
        for message_id, record_history_id in candidates:
            last_history_id = record_history_id
            try:
                message = self._messages.get_message(message_id)
            except GmailError as exc:
                logger.warning(
                    "Gmail history message retrieval failed message_id=%s error=%s",
                    message_id,
                    type(exc).__name__,
                )
                failed += 1
                continue

            topic_id = _first_matching_topic(message.label_ids, label_topic_map)
            if topic_id is None:
                # Message no longer carries a monitored label (e.g. removed,
                # or only ever matched an unrelated label) — not an error.
                continue

            outcome = self._ingest.ingest_message(
                message, topic_id=topic_id, account_id=account_id
            )
            processed += 1
            if outcome.status == "CREATED":
                created += 1
                if self._on_event_created is not None and outcome.domain_event:
                    self._on_event_created(outcome.domain_event)
            elif outcome.status == "DUPLICATE":
                duplicate += 1
            else:
                failed += 1

        new_cursor = (
            last_history_id if truncated else (final_history_id or last_history_id)
        )
        return HistorySyncOutcome(
            processed_message_count=processed,
            created_count=created,
            duplicate_count=duplicate,
            failed_count=failed,
            new_history_id=new_cursor,
            has_more=truncated,
        )

    def _collect_candidates(
        self, start_history_id: str
    ) -> tuple[list[tuple[str, str]], str | None, bool]:
        """Page through history, returning up to ``batch_size`` distinct
        (message_id, record_history_id) candidates in encounter order,
        the final page's top-level history_id, and whether more remain.
        """
        seen: set[str] = set()
        candidates: list[tuple[str, str]] = []
        page_token: str | None = None
        final_history_id: str | None = None
        truncated = False

        while True:
            page = self._history.list_history(
                start_history_id=start_history_id,
                page_token=page_token,
                max_results=self._page_size,
            )
            if page.history_id is not None:
                final_history_id = page.history_id
            for record in page.records:
                if record.message_id in seen:
                    continue
                if len(candidates) >= self._batch_size:
                    truncated = True
                    break
                seen.add(record.message_id)
                candidates.append((record.message_id, record.history_id))
            if truncated:
                break
            page_token = page.next_page_token
            if page_token is None:
                break
        return candidates, final_history_id, truncated


def _first_matching_topic(
    label_ids: tuple[str, ...], label_topic_map: dict[str, str]
) -> str | None:
    for label_id in label_ids:
        topic_id = label_topic_map.get(label_id)
        if topic_id is not None:
            return topic_id
    return None
