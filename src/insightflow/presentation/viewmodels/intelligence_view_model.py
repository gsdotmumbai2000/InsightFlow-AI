"""Intelligence list/detail presentation state."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.application.dto.models import AIAnalysisDto, IntelligenceEventDto
from insightflow.application.exceptions import AIAnalysisNotFoundError
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash, format_timestamp


@dataclass(frozen=True, slots=True)
class IntelligenceListRow:
    id: str
    priority: str
    topic_id: str
    title: str
    received_at: str
    status: str


@dataclass(frozen=True, slots=True)
class EventDetailsState:
    event_id: str
    title: str
    topic_id: str
    source_type: str
    source_id: str
    external_id: str
    received_at: str
    source_published_at: str
    status: str
    priority: str
    ai_available: bool
    summary: str
    why_it_matters: str
    key_facts: tuple[str, ...]
    what_to_watch: tuple[str, ...]
    market_impact: str
    ai_message: str


@dataclass(frozen=True, slots=True)
class IntelligenceViewState:
    rows: tuple[IntelligenceListRow, ...]
    selected: EventDetailsState | None
    error_message: str | None = None
    empty_message: str | None = None


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
        rows = tuple(self._row(event) for event in events)
        if self._selected_id is None or self._selected_id not in {
            row.id for row in rows
        }:
            self._selected_id = rows[0].id
        details = self._load_details(self._selected_id)
        return IntelligenceViewState(rows=rows, selected=details)

    def select(self, event_id: str) -> IntelligenceViewState:
        return self.load(selected_event_id=event_id)

    def _load_details(self, event_id: str) -> EventDetailsState | None:
        try:
            event = self._executor.run(
                lambda: self._use_cases.get_intelligence_event.execute(event_id)
            )
        except Exception as exc:
            return EventDetailsState(
                event_id=event_id,
                title="—",
                topic_id="—",
                source_type="—",
                source_id="—",
                external_id="—",
                received_at="—",
                source_published_at="—",
                status="—",
                priority="—",
                ai_available=False,
                summary="",
                why_it_matters="",
                key_facts=(),
                what_to_watch=(),
                market_impact="",
                ai_message=user_message_for_error(exc),
            )
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
                analysis=None,
                ai_message=user_message_for_error(exc),
            )
        if analysis is None:
            return self._details_from_event(
                event,
                analysis=None,
                ai_message="AI analysis not available",
            )
        return self._details_from_event(event, analysis=analysis, ai_message="")

    @staticmethod
    def _row(event: IntelligenceEventDto) -> IntelligenceListRow:
        return IntelligenceListRow(
            id=event.id,
            priority=display_or_dash(event.priority),
            topic_id=display_or_dash(event.topic_id),
            title=display_or_dash(event.title),
            received_at=format_timestamp(event.received_at),
            status=event.status,
        )

    @staticmethod
    def _details_from_event(
        event: IntelligenceEventDto,
        *,
        analysis: AIAnalysisDto | None,
        ai_message: str,
    ) -> EventDetailsState:
        market = "—"
        if analysis and analysis.market_impact is not None:
            impact = analysis.market_impact
            assets = ", ".join(impact.affected_assets) or "—"
            market = (
                f"{impact.direction} | relevance={impact.relevance} | "
                f"assets={assets} | confidence={impact.confidence:.2f}\n"
                f"{impact.reasoning}"
            )
        return EventDetailsState(
            event_id=event.id,
            title=display_or_dash(event.title),
            topic_id=display_or_dash(event.topic_id),
            source_type=event.source.source_type,
            source_id=event.source.source_id,
            external_id=event.source.external_id,
            received_at=format_timestamp(event.received_at),
            source_published_at=format_timestamp(event.source_published_at),
            status=event.status,
            priority=display_or_dash(event.priority),
            ai_available=analysis is not None,
            summary=analysis.summary if analysis else "",
            why_it_matters=(analysis.why_it_matters or "") if analysis else "",
            key_facts=analysis.key_facts if analysis else (),
            what_to_watch=analysis.what_to_watch if analysis else (),
            market_impact=market if analysis else "",
            ai_message=ai_message,
        )
