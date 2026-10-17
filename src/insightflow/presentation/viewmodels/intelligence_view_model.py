"""Intelligence list/detail presentation state."""

from __future__ import annotations

from dataclasses import dataclass, replace

from insightflow.application.dto.models import (
    AIAnalysisDto,
    AttachmentDto,
    IntelligenceEventDto,
    ReprocessAIRequest,
)
from insightflow.application.exceptions import AIAnalysisNotFoundError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash, format_timestamp

_NO_CONTENT_MESSAGE = "No email content available."
_AI_NOT_AVAILABLE = "AI analysis not available."
_AI_IN_PROGRESS = "AI analysis in progress..."
_AI_FAILED_PREFIX = "AI analysis failed."


@dataclass(frozen=True, slots=True)
class IntelligenceListRow:
    id: str
    priority: str
    topic_id: str
    topic_name: str
    title: str
    received_at: str
    status: str


@dataclass(frozen=True, slots=True)
class EventDetailsState:
    event_id: str
    title: str
    topic_id: str
    topic_name: str
    source_type: str
    source_id: str
    external_id: str
    thread_id: str
    received_at: str
    source_published_at: str
    status: str
    priority: str
    content: str
    attachments: tuple[str, ...]
    ai_available: bool
    ai_status_label: str
    summary: str
    why_it_matters: str
    key_facts: tuple[str, ...]
    what_to_watch: tuple[str, ...]
    market_impact: str
    entities: tuple[str, ...]
    sentiment: str
    confidence: str
    ai_message: str
    can_reanalyze: bool
    generated_content: str = ""  # CUSTOM_TEXT profiles only


@dataclass(frozen=True, slots=True)
class IntelligenceViewState:
    rows: tuple[IntelligenceListRow, ...]
    selected: EventDetailsState | None
    error_message: str | None = None
    empty_message: str | None = None
    info_message: str | None = None


class IntelligenceViewModel:
    def __init__(
        self,
        use_cases: ApplicationUseCases,
        *,
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._executor = executor or UiExecutor()
        self._selected_id: str | None = None

    def load(self, *, selected_event_id: str | None = None) -> IntelligenceViewState:
        if selected_event_id is not None:
            self._selected_id = selected_event_id
        try:
            events = self._executor.run(
                lambda: self._use_cases.list_recent_intelligence_events.execute(
                    limit=100
                )
            )
        except Exception as exc:
            return IntelligenceViewState(
                rows=(),
                selected=None,
                error_message=user_message_for_error(exc),
            )
        if not events:
            self._selected_id = None
            return IntelligenceViewState(
                rows=(),
                selected=None,
                empty_message="No intelligence events yet.",
            )
        topic_names = self._topic_name_map()
        rows = tuple(self._row(event, topic_names) for event in events)
        if self._selected_id is None or self._selected_id not in {
            row.id for row in rows
        }:
            self._selected_id = rows[0].id
        details = self._load_details(self._selected_id, topic_names)
        return IntelligenceViewState(rows=rows, selected=details)

    def select(self, event_id: str) -> IntelligenceViewState:
        return self.load(selected_event_id=event_id)

    def clear_all(self) -> IntelligenceViewState:
        """Delete every event with its AI analyses and notifications."""
        try:
            deleted = self._executor.run(
                lambda: self._use_cases.clear_all_intelligence_events.execute()
            )
        except Exception as exc:
            return replace(self.load(), error_message=user_message_for_error(exc))
        self._selected_id = None
        return replace(
            self.load(),
            info_message=(
                f"Cleared {deleted} intelligence event(s). Cleared emails will "
                "not be imported again."
            ),
        )

    def _topic_name_map(self) -> dict[str, str]:
        """Resolve topic_id -> name via the application layer (no repo access).

        Falls back to an empty map (display shows the id) if topics cannot
        be loaded; a topic-name lookup failure must not hide the event list.
        """
        try:
            topics = self._executor.run(lambda: self._use_cases.list_topics.execute())
        except Exception:
            return {}
        return {topic.id: topic.name for topic in topics}

    def _load_details(
        self, event_id: str, topic_names: dict[str, str]
    ) -> EventDetailsState | None:
        try:
            event = self._executor.run(
                lambda: self._use_cases.get_intelligence_event.execute(event_id)
            )
        except Exception as exc:
            return EventDetailsState(
                event_id=event_id,
                title="—",
                topic_id="—",
                topic_name="—",
                source_type="—",
                source_id="—",
                external_id="—",
                thread_id="—",
                received_at="—",
                source_published_at="—",
                status="—",
                priority="—",
                content=_NO_CONTENT_MESSAGE,
                attachments=(),
                ai_available=False,
                ai_status_label=_AI_NOT_AVAILABLE,
                summary="",
                why_it_matters="",
                key_facts=(),
                what_to_watch=(),
                market_impact="",
                entities=(),
                sentiment="—",
                confidence="—",
                ai_message=user_message_for_error(exc),
                can_reanalyze=False,
            )
        attachments = self._load_attachments(event_id)
        analysis: AIAnalysisDto | None
        try:
            analysis = self._executor.run(
                lambda: self._use_cases.get_ai_analysis.execute(event_id)
            )
        except AIAnalysisNotFoundError:
            analysis = None
        except Exception as exc:
            return self._details_from_event(
                event,
                topic_names,
                attachments,
                analysis=None,
                ai_message=user_message_for_error(exc),
            )
        if analysis is None:
            return self._details_from_event(
                event,
                topic_names,
                attachments,
                analysis=None,
                ai_message=(
                    _AI_IN_PROGRESS
                    if event.status == "AI_PROCESSING"
                    else _AI_NOT_AVAILABLE
                ),
            )
        return self._details_from_event(
            event, topic_names, attachments, analysis=analysis, ai_message=""
        )

    def reanalyze(self, event_id: str) -> IntelligenceViewState:
        """Queue (re-)analysis for an event and refresh the view.

        Enqueuing is fast (a DB read plus a queue put) — the actual AI call
        happens later on the background AI worker, so this never blocks
        the GUI thread.
        """
        try:
            self._executor.run(
                lambda: self._use_cases.reprocess_ai_analysis.execute(
                    ReprocessAIRequest(event_id=event_id)
                )
            )
        except Exception as exc:
            state = self.load(selected_event_id=event_id)
            return replace(state, error_message=user_message_for_error(exc))
        return self.load(selected_event_id=event_id)

    def _load_attachments(self, event_id: str) -> tuple[AttachmentDto, ...]:
        try:
            return tuple(
                self._executor.run(
                    lambda: self._use_cases.list_event_attachments.execute(event_id)
                )
            )
        except Exception:
            return ()

    @staticmethod
    def _topic_display(topic_id: str | None, topic_names: dict[str, str]) -> str:
        if not topic_id:
            return "—"
        return topic_names.get(topic_id, topic_id)

    @staticmethod
    def _format_attachment(attachment: AttachmentDto) -> str:
        mime_type = attachment.content_type or "unknown type"
        size = (
            f"{attachment.size_bytes} bytes"
            if attachment.size_bytes is not None
            else "unknown size"
        )
        return f"{attachment.filename} ({mime_type}, {size})"

    @classmethod
    def _row(
        cls, event: IntelligenceEventDto, topic_names: dict[str, str]
    ) -> IntelligenceListRow:
        return IntelligenceListRow(
            id=event.id,
            priority=display_or_dash(event.priority),
            topic_id=display_or_dash(event.topic_id),
            topic_name=cls._topic_display(event.topic_id, topic_names),
            title=display_or_dash(event.title),
            received_at=format_timestamp(event.received_at),
            status=event.status,
        )

    @classmethod
    def _details_from_event(
        cls,
        event: IntelligenceEventDto,
        topic_names: dict[str, str],
        attachments: tuple[AttachmentDto, ...],
        *,
        analysis: AIAnalysisDto | None,
        ai_message: str,
    ) -> EventDetailsState:
        market = ""  # empty: no assessment — the view hides the section
        if analysis and analysis.market_impact is not None:
            impact = analysis.market_impact
            assets = ", ".join(impact.affected_assets) or "—"
            market = (
                f"{impact.direction} | relevance={impact.relevance} | "
                f"assets={assets} | confidence={impact.confidence:.2f}\n"
                f"{impact.reasoning}"
            )
        content = event.normalized_content.strip() if event.normalized_content else ""
        completed = analysis is not None and analysis.status == "COMPLETED"
        if analysis is None:
            ai_status_label = ai_message or _AI_NOT_AVAILABLE
        elif analysis.status == "FAILED":
            reason = analysis.failure_reason or ""
            ai_status_label = f"{_AI_FAILED_PREFIX} {reason}".strip()
        elif completed:
            ai_status_label = "Completed"
        else:
            ai_status_label = analysis.status
        return EventDetailsState(
            event_id=event.id,
            title=display_or_dash(event.title),
            topic_id=display_or_dash(event.topic_id),
            topic_name=cls._topic_display(event.topic_id, topic_names),
            source_type=event.source.source_type,
            source_id=event.source.source_id,
            external_id=event.source.external_id,
            thread_id=display_or_dash(event.source.thread_id),
            received_at=format_timestamp(event.received_at),
            source_published_at=format_timestamp(event.source_published_at),
            status=event.status,
            priority=display_or_dash(event.priority),
            content=content or _NO_CONTENT_MESSAGE,
            attachments=tuple(cls._format_attachment(item) for item in attachments),
            ai_available=completed,
            ai_status_label=ai_status_label,
            summary=analysis.summary if completed and analysis else "",
            why_it_matters=(
                (analysis.why_it_matters or "") if completed and analysis else ""
            ),
            key_facts=analysis.key_facts if completed and analysis else (),
            what_to_watch=analysis.what_to_watch if completed and analysis else (),
            market_impact=market if completed and analysis else "",
            entities=analysis.entities if completed and analysis else (),
            sentiment=(analysis.sentiment or "—") if completed and analysis else "—",
            confidence=(
                f"{analysis.confidence:.2f}"
                if completed and analysis and analysis.confidence is not None
                else "—"
            ),
            ai_message=ai_message,
            can_reanalyze=True,
            generated_content=(
                (analysis.generated_content or "") if completed and analysis else ""
            ),
        )
