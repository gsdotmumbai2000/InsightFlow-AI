"""Topics page presentation state and actions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from insightflow.application.dto.models import CreateTopicRequest, TopicDto
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash


@dataclass(frozen=True, slots=True)
class TopicRow:
    id: str
    name: str
    description: str
    status: str
    ai_profile: str


@dataclass(frozen=True, slots=True)
class TopicsViewState:
    rows: tuple[TopicRow, ...]
    selected_id: str | None = None
    error_message: str | None = None
    info_message: str | None = None
    empty_message: str | None = None


class TopicsViewModel:
    def __init__(
        self,
        use_cases: ApplicationUseCases,
        *,
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._executor = executor or UiExecutor()
        self._selected_id: str | None = None

    def load(self, *, selected_id: str | None = None) -> TopicsViewState:
        if selected_id is not None:
            self._selected_id = selected_id
        try:
            topics = self._executor.run(lambda: self._use_cases.list_topics.execute())
        except Exception as exc:
            return TopicsViewState(
                rows=(),
                error_message=user_message_for_error(exc),
            )
        rows = tuple(self._row(topic) for topic in topics)
        if self._selected_id and self._selected_id not in {row.id for row in rows}:
            self._selected_id = None
        return TopicsViewState(
            rows=rows,
            selected_id=self._selected_id,
            empty_message=None if rows else "No topics configured yet.",
        )

    def select(self, topic_id: str) -> TopicsViewState:
        self._selected_id = topic_id
        return self.load()

    def create_topic(
        self,
        *,
        name: str,
        description: str | None,
        ai_profile_id: str | None,
        source_type: str = "GENERIC",
        source_id: str = "local",
        source_identifier: str | None = None,
    ) -> TopicsViewState:
        request = CreateTopicRequest(
            name=name.strip(),
            description=(description.strip() if description else None),
            source_type=source_type,
            source_id=source_id,
            source_identifier=source_identifier or f"manual-{uuid4()}",
            ai_profile_id=ai_profile_id.strip() if ai_profile_id else None,
        )
        try:
            created = self._executor.run(
                lambda: self._use_cases.create_topic.execute(request)
            )
        except Exception as exc:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                error_message=user_message_for_error(exc),
            )
        self._selected_id = created.id
        state = self.load()
        return TopicsViewState(
            rows=state.rows,
            selected_id=created.id,
            info_message=f"Created topic '{created.name}'.",
        )

    def enable(self) -> TopicsViewState:
        return self._transition("enable")

    def disable(self) -> TopicsViewState:
        return self._transition("disable")

    def pause(self) -> TopicsViewState:
        return self._transition("pause")

    def resume(self) -> TopicsViewState:
        return self._transition("resume")

    def _transition(self, action: str) -> TopicsViewState:
        if not self._selected_id:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=None,
                error_message="Select a topic first.",
            )
        topic_id = self._selected_id
        try:
            if action == "enable":
                self._executor.run(
                    lambda: self._use_cases.enable_topic.execute(topic_id)
                )
            elif action == "disable":
                self._executor.run(
                    lambda: self._use_cases.disable_topic.execute(topic_id)
                )
            elif action == "pause":
                self._executor.run(
                    lambda: self._use_cases.pause_topic.execute(topic_id)
                )
            elif action == "resume":
                self._executor.run(
                    lambda: self._use_cases.resume_topic.execute(topic_id)
                )
        except Exception as exc:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=topic_id,
                error_message=user_message_for_error(exc),
            )
        return self.load(selected_id=topic_id)

    @staticmethod
    def _row(topic: TopicDto) -> TopicRow:
        return TopicRow(
            id=topic.id,
            name=topic.name,
            description=display_or_dash(topic.description),
            status=topic.status,
            ai_profile=display_or_dash(topic.ai_profile_id),
        )
