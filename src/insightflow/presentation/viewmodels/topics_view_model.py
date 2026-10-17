"""Topics page presentation state and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from insightflow.application.dto.email import (
    IngestTopicMessagesRequest,
    RetrieveTopicMessagesRequest,
)
from insightflow.application.dto.models import (
    AIProfileDto,
    CreateAIProfileRequest,
    CreateTopicRequest,
    TopicDto,
    UpdateAIProfileRequest,
    UpdateTopicRequest,
)
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash

# Manual test retrieval (Phase 8): small, deliberately bounded default so a
# user testing "Retrieve recent messages" never accidentally pulls a large
# amount of mail.
MANUAL_RETRIEVAL_MAX_MESSAGES = 5

# Manual test ingestion (Phase 9): same conservative default for "Save
# recent messages", which persists IntelligenceEvent records.
MANUAL_INGEST_MAX_MESSAGES = 5

_NOT_CONFIGURED = "Not configured"


@dataclass(frozen=True, slots=True)
class TopicRow:
    id: str
    name: str
    description: str
    status: str
    ai_profile: str
    source_type: str


@dataclass(frozen=True, slots=True)
class AIProfileOption:
    """One selectable entry for the Topics page's AI-profile picker."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class TopicsViewState:
    rows: tuple[TopicRow, ...]
    selected_id: str | None = None
    selected_ai_profile_id: str | None = None
    ai_profile_options: tuple[AIProfileOption, ...] = field(default_factory=tuple)
    error_message: str | None = None
    info_message: str | None = None
    empty_message: str | None = None
    busy: bool = False


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
        self._busy = False

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
        profiles = self._load_profiles()
        profile_names = {profile.id: profile.name for profile in profiles}
        rows = tuple(self._row(topic, profile_names) for topic in topics)
        if self._selected_id and self._selected_id not in {row.id for row in rows}:
            self._selected_id = None
        selected_ai_profile_id: str | None = None
        if self._selected_id:
            selected_topic = next(
                (topic for topic in topics if topic.id == self._selected_id), None
            )
            if selected_topic is not None:
                selected_ai_profile_id = selected_topic.ai_profile_id
        return TopicsViewState(
            rows=rows,
            selected_id=self._selected_id,
            selected_ai_profile_id=selected_ai_profile_id,
            ai_profile_options=tuple(
                AIProfileOption(id=profile.id, name=profile.name)
                for profile in profiles
            ),
            empty_message=None if rows else "No topics configured yet.",
            busy=self._busy,
        )

    def _load_profiles(self) -> list[AIProfileDto]:
        try:
            return self._executor.run(
                lambda: self._use_cases.list_ai_profiles.execute()
            )
        except Exception:
            # A profile-list failure must not hide the Topics list itself.
            return []

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
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load(selected_id=created.id)
        return TopicsViewState(
            rows=state.rows,
            selected_id=created.id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=f"Created topic '{created.name}'.",
        )

    def create_ai_profile(
        self,
        *,
        name: str,
        description: str | None,
        instructions: str,
        output_schema_version: str,
        assign_to_selected_topic: bool,
        output_style: str = "ANALYSIS",
    ) -> TopicsViewState:
        """Create a new AI profile, optionally assigning it to the selected Topic.

        Creation goes through ``CreateAIProfileUseCase`` only; assignment
        reuses the existing ``UpdateTopicUseCase`` — no repository access
        happens here.
        """
        request = CreateAIProfileRequest(
            name=name.strip(),
            instructions=instructions.strip(),
            output_schema_version=output_schema_version.strip() or "v1",
            description=(description.strip() if description else None),
            output_style=output_style,
        )
        try:
            created = self._executor.run(
                lambda: self._use_cases.create_ai_profile.execute(request)
            )
        except Exception as exc:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        if assign_to_selected_topic and self._selected_id:
            return self._assign_profile(
                self._selected_id,
                created.id,
                success_message=(
                    f"Created AI profile '{created.name}' and assigned it "
                    "to the selected topic."
                ),
            )
        state = self.load(selected_id=self._selected_id)
        return TopicsViewState(
            rows=state.rows,
            selected_id=state.selected_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=f"Created AI profile '{created.name}'.",
        )

    def get_ai_profile(self, profile_id: str) -> AIProfileDto | None:
        """The profile to pre-fill the edit dialog with, or ``None`` if gone."""
        try:
            return self._executor.run(
                lambda: self._use_cases.get_ai_profile.execute(profile_id)
            )
        except Exception:
            return None

    def update_ai_profile(
        self,
        *,
        profile_id: str,
        name: str,
        description: str | None,
        instructions: str,
        output_style: str | None = None,
    ) -> TopicsViewState:
        request = UpdateAIProfileRequest(
            profile_id=profile_id,
            name=name.strip(),
            instructions=instructions.strip(),
            description=(description.strip() if description else None),
            output_style=output_style,
        )
        try:
            updated = self._executor.run(
                lambda: self._use_cases.update_ai_profile.execute(request)
            )
        except Exception as exc:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load()
        return TopicsViewState(
            rows=state.rows,
            selected_id=state.selected_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=(
                f"Saved AI profile '{updated.name}' (version {updated.version})."
            ),
        )

    def delete_ai_profile(self, profile_id: str) -> TopicsViewState:
        """Delete a profile; topics using it go back to "Not configured"."""
        name = next(
            (
                option.name
                for option in self._load_profile_options()
                if option.id == profile_id
            ),
            "AI profile",
        )
        try:
            self._executor.run(
                lambda: self._use_cases.delete_ai_profile.execute(profile_id)
            )
        except Exception as exc:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load()
        return TopicsViewState(
            rows=state.rows,
            selected_id=state.selected_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=(
                f"Deleted AI profile '{name}'. Topics that used it now have no "
                "AI profile; earlier analyses are kept."
            ),
        )

    def assign_ai_profile(self, ai_profile_id: str | None) -> TopicsViewState:
        """Attach (or clear, if ``None``) an AI profile on the selected Topic."""
        if not self._selected_id:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                ai_profile_options=state.ai_profile_options,
                error_message="Select a topic first.",
            )
        profile_name = next(
            (
                option.name
                for option in self._load_profile_options()
                if option.id == ai_profile_id
            ),
            None,
        )
        message = (
            f"Assigned AI profile '{profile_name}' to the selected topic."
            if profile_name
            else "Cleared the AI profile for the selected topic."
        )
        return self._assign_profile(
            self._selected_id, ai_profile_id, success_message=message
        )

    def _load_profile_options(self) -> tuple[AIProfileOption, ...]:
        return tuple(
            AIProfileOption(id=profile.id, name=profile.name)
            for profile in self._load_profiles()
        )

    def _assign_profile(
        self, topic_id: str, ai_profile_id: str | None, *, success_message: str
    ) -> TopicsViewState:
        request = UpdateTopicRequest(
            topic_id=topic_id,
            ai_profile_id=ai_profile_id,
            clear_ai_profile=ai_profile_id is None,
        )
        try:
            self._executor.run(lambda: self._use_cases.update_topic.execute(request))
        except Exception as exc:
            state = self.load(selected_id=topic_id)
            return TopicsViewState(
                rows=state.rows,
                selected_id=state.selected_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load(selected_id=topic_id)
        return TopicsViewState(
            rows=state.rows,
            selected_id=state.selected_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=success_message,
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
                ai_profile_options=state.ai_profile_options,
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
            state = self.load(selected_id=topic_id)
            return TopicsViewState(
                rows=state.rows,
                selected_id=topic_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        return self.load(selected_id=topic_id)

    def set_busy(self, busy: bool) -> TopicsViewState:
        self._busy = busy
        return self.load()

    def retrieve_recent_messages(
        self, *, max_messages: int = MANUAL_RETRIEVAL_MAX_MESSAGES
    ) -> TopicsViewState:
        """Manual test action (Phase 8): fetch a few recent Gmail messages.

        Runs through the application use case only; never creates
        IntelligenceEvent records and never logs/display message bodies.
        """
        if not self._selected_id:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=None,
                ai_profile_options=state.ai_profile_options,
                error_message="Select a topic first.",
            )
        topic_id = self._selected_id
        try:
            result = self._executor.run(
                lambda: self._use_cases.retrieve_topic_messages.execute(
                    RetrieveTopicMessagesRequest(
                        topic_id=topic_id, max_messages=max_messages
                    )
                )
            )
        except Exception as exc:
            state = self.load(selected_id=topic_id)
            return TopicsViewState(
                rows=state.rows,
                selected_id=topic_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load(selected_id=topic_id)
        summary = f"Retrieved {len(result.messages)} message(s)"
        if result.failed:
            summary += f", {len(result.failed)} failed"
        if result.has_more:
            summary += " (more available)"
        return TopicsViewState(
            rows=state.rows,
            selected_id=topic_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=summary + ".",
        )

    def save_recent_messages(
        self, *, max_messages: int = MANUAL_INGEST_MAX_MESSAGES
    ) -> TopicsViewState:
        """Manual test action (Phase 9): persist a few recent Gmail messages.

        Creates IntelligenceEvent (+ attachment metadata) records via the
        application use case; never logs/displays message bodies.
        """
        if not self._selected_id:
            state = self.load()
            return TopicsViewState(
                rows=state.rows,
                selected_id=None,
                ai_profile_options=state.ai_profile_options,
                error_message="Select a topic first.",
            )
        topic_id = self._selected_id
        try:
            result = self._executor.run(
                lambda: self._use_cases.ingest_topic_messages.execute(
                    IngestTopicMessagesRequest(
                        topic_id=topic_id, max_messages=max_messages
                    )
                )
            )
        except Exception as exc:
            state = self.load(selected_id=topic_id)
            return TopicsViewState(
                rows=state.rows,
                selected_id=topic_id,
                selected_ai_profile_id=state.selected_ai_profile_id,
                ai_profile_options=state.ai_profile_options,
                error_message=user_message_for_error(exc),
            )
        state = self.load(selected_id=topic_id)
        summary = f"Saved {len(result.created)} new event(s)"
        if result.duplicate_count:
            summary += f", {result.duplicate_count} already stored"
        if result.failed:
            summary += f", {len(result.failed)} failed"
        if result.has_more:
            summary += " (more available)"
        return TopicsViewState(
            rows=state.rows,
            selected_id=topic_id,
            selected_ai_profile_id=state.selected_ai_profile_id,
            ai_profile_options=state.ai_profile_options,
            info_message=summary + ".",
        )

    @staticmethod
    def _row(topic: TopicDto, profile_names: dict[str, str]) -> TopicRow:
        ai_profile = _NOT_CONFIGURED
        if topic.ai_profile_id:
            ai_profile = profile_names.get(topic.ai_profile_id, _NOT_CONFIGURED)
        return TopicRow(
            id=topic.id,
            name=topic.name,
            description=display_or_dash(topic.description),
            status=topic.status,
            ai_profile=ai_profile,
            source_type=topic.source.source_type,
        )
