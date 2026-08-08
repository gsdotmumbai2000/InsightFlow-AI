"""Settings presentation state including Gmail connection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from insightflow.application.dto.gmail import GmailLabelDto
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.configuration.directories import AppDirectories
from insightflow.configuration.models import AppConfig
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash


@dataclass(frozen=True, slots=True)
class SettingsViewState:
    rows: tuple[tuple[str, str], ...]
    gmail_status: str
    gmail_account: str
    gmail_message: str
    labels: tuple[GmailLabelDto, ...]
    selected_label_id: str | None
    topics: tuple[tuple[str, str], ...]  # id, name
    selected_topic_id: str | None
    busy: bool = False
    error_message: str | None = None
    info_message: str | None = None


class SettingsViewModel:
    def __init__(
        self,
        *,
        use_cases: ApplicationUseCases,
        config: AppConfig,
        directories: AppDirectories,
        database_path: Path,
        diagnostics: RuntimeDiagnostics,
        executor: UiExecutor | None = None,
    ) -> None:
        self._use_cases = use_cases
        self._config = config
        self._directories = directories
        self._database_path = database_path
        self._diagnostics = diagnostics
        self._executor = executor or UiExecutor()
        self._selected_label_id: str | None = None
        self._selected_topic_id: str | None = None
        self._labels: tuple[GmailLabelDto, ...] = ()
        self._busy = False

    def load(self) -> SettingsViewState:
        rows = (
            ("Application", self._config.application.name),
            ("Version", self._config.application.version),
            ("Environment", self._config.application.environment.value),
            ("Data directory", str(self._directories.root)),
            ("Log directory", str(self._directories.logs)),
            ("Database directory", str(self._directories.database)),
            ("Database file", str(self._database_path)),
            ("Log level", self._config.logging.level.value),
            ("Secret store backend", self._diagnostics.secret_store_backend),
        )
        try:
            status = self._executor.run(
                lambda: self._use_cases.get_gmail_connection_status.execute()
            )
            topics = self._executor.run(lambda: self._use_cases.list_topics.execute())
        except Exception as exc:
            return SettingsViewState(
                rows=rows,
                gmail_status="CONNECTION_FAILED",
                gmail_account="—",
                gmail_message=user_message_for_error(exc),
                labels=(),
                selected_label_id=None,
                topics=(),
                selected_topic_id=None,
                busy=self._busy,
                error_message=user_message_for_error(exc),
            )

        account = "—"
        if status.account is not None:
            account = status.account.email
        topic_rows = tuple((topic.id, topic.name) for topic in topics)
        if self._selected_topic_id and self._selected_topic_id not in {
            item[0] for item in topic_rows
        }:
            self._selected_topic_id = None
        return SettingsViewState(
            rows=rows,
            gmail_status=status.status,
            gmail_account=account,
            gmail_message=display_or_dash(status.message),
            labels=self._labels,
            selected_label_id=self._selected_label_id,
            topics=topic_rows,
            selected_topic_id=self._selected_topic_id,
            busy=self._busy,
        )

    def set_busy(self, busy: bool) -> SettingsViewState:
        self._busy = busy
        return self.load()

    def connect_gmail(self) -> SettingsViewState:
        try:
            account = self._executor.run(
                lambda: self._use_cases.connect_gmail.execute()
            )
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=account.email,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                info_message=f"Connected as {account.email}",
            )
        except Exception as exc:
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                error_message=user_message_for_error(exc),
            )

    def disconnect_gmail(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.disconnect_gmail.execute())
            self._labels = ()
            self._selected_label_id = None
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=(),
                selected_label_id=None,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                info_message="Gmail disconnected.",
            )
        except Exception as exc:
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                error_message=user_message_for_error(exc),
            )

    def refresh_labels(self) -> SettingsViewState:
        try:
            labels = self._executor.run(
                lambda: self._use_cases.list_gmail_labels.execute()
            )
            self._labels = tuple(labels)
            if self._selected_label_id and self._selected_label_id not in {
                label.label_id for label in self._labels
            }:
                self._selected_label_id = None
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=self._labels,
                selected_label_id=self._selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                info_message=f"Loaded {len(self._labels)} labels.",
            )
        except Exception as exc:
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                busy=False,
                error_message=user_message_for_error(exc),
            )

    def select_label(self, label_id: str) -> None:
        """Remember the selected label without reloading Settings state."""
        self._selected_label_id = label_id

    def select_topic(self, topic_id: str) -> None:
        """Remember the selected topic without reloading Settings state."""
        self._selected_topic_id = topic_id

    def map_selected_label_to_topic(self) -> SettingsViewState:
        from insightflow.application.dto.gmail import MapGmailLabelToTopicRequest

        if not self._selected_label_id:
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                error_message="Select a Gmail label first.",
            )
        label_name = None
        for label in self._labels:
            if label.label_id == self._selected_label_id:
                label_name = label.name
                break
        request = MapGmailLabelToTopicRequest(
            label_id=self._selected_label_id,
            topic_id=self._selected_topic_id,
            topic_name=label_name,
            label_name=label_name,
        )
        try:
            mapping = self._executor.run(
                lambda: self._use_cases.map_gmail_label_to_topic.execute(request)
            )
            self._selected_topic_id = mapping.topic_id
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=mapping.topic_id,
                info_message=(
                    f"Mapped label '{mapping.label_name or mapping.label_id}' "
                    f"to topic '{mapping.topic_name}'."
                ),
            )
        except Exception as exc:
            state = self.load()
            return SettingsViewState(
                rows=state.rows,
                gmail_status=state.gmail_status,
                gmail_account=state.gmail_account,
                gmail_message=state.gmail_message,
                labels=state.labels,
                selected_label_id=state.selected_label_id,
                topics=state.topics,
                selected_topic_id=state.selected_topic_id,
                error_message=user_message_for_error(exc),
            )
