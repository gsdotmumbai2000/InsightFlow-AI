"""Settings presentation state including Gmail connection and monitoring."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from insightflow.application.dto.ai import AIOutputTokenLimitDto
from insightflow.application.dto.gmail import GmailLabelDto
from insightflow.application.use_cases import ApplicationUseCases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.configuration.directories import AppDirectories
from insightflow.configuration.models import AppConfig
from insightflow.presentation.errors import user_message_for_error
from insightflow.presentation.executor import UiExecutor
from insightflow.presentation.formatting import display_or_dash, format_timestamp


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
    # -- Real-time monitoring (Phase 10) --------------------------------
    monitoring_status: str = "NOT_CONFIGURED"
    monitoring_account_email: str = "—"
    monitoring_watched_topics: str = "—"
    monitoring_pubsub_project: str = "—"
    monitoring_pubsub_topic: str = "—"
    monitoring_pubsub_subscription: str = "—"
    monitoring_watch_expiration: str = "—"
    monitoring_last_sync: str = "—"
    monitoring_last_notification: str = "—"
    monitoring_last_error: str = "—"
    pubsub_connected: bool = False
    # -- Windows auto-start (Phase 13) -----------------------------------
    startup_registered: bool = False
    # -- AI output token limit -------------------------------------------
    ai_output_tokens: AIOutputTokenLimitDto | None = None
    ai_analysis_enabled: bool | None = None  # None: could not be read


@dataclass(frozen=True, slots=True)
class _MonitoringFields:
    """Precisely typed intermediate — avoids **dict unpacking into a dataclass."""

    status: str = "NOT_CONFIGURED"
    account_email: str = "—"
    watched_topics: str = "—"
    pubsub_project: str = "—"
    pubsub_topic: str = "—"
    pubsub_subscription: str = "—"
    watch_expiration: str = "—"
    last_sync: str = "—"
    last_notification: str = "—"
    last_error: str = "—"
    pubsub_connected: bool = False


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

        monitoring = self._load_monitoring_fields()
        try:
            startup_registered = self._executor.run(
                lambda: self._use_cases.get_startup_registration_status.execute()
            )
        except Exception:
            startup_registered = False
        try:
            ai_output_tokens: AIOutputTokenLimitDto | None = self._executor.run(
                lambda: self._use_cases.get_ai_output_token_limit.execute()
            )
        except Exception:
            ai_output_tokens = None
        try:
            ai_analysis_enabled: bool | None = self._executor.run(
                lambda: self._use_cases.get_ai_analysis_enabled.execute()
            )
        except Exception:
            ai_analysis_enabled = None
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
            monitoring_status=monitoring.status,
            monitoring_account_email=monitoring.account_email,
            monitoring_watched_topics=monitoring.watched_topics,
            monitoring_pubsub_project=monitoring.pubsub_project,
            monitoring_pubsub_topic=monitoring.pubsub_topic,
            monitoring_pubsub_subscription=monitoring.pubsub_subscription,
            monitoring_watch_expiration=monitoring.watch_expiration,
            monitoring_last_sync=monitoring.last_sync,
            monitoring_last_notification=monitoring.last_notification,
            monitoring_last_error=monitoring.last_error,
            pubsub_connected=monitoring.pubsub_connected,
            startup_registered=startup_registered,
            ai_output_tokens=ai_output_tokens,
            ai_analysis_enabled=ai_analysis_enabled,
        )

    def set_ai_analysis_enabled(self, enabled: bool) -> SettingsViewState:
        try:
            cancelled = self._executor.run(
                lambda: self._use_cases.set_ai_analysis_enabled.execute(enabled)
            )
        except Exception as exc:
            return replace(self.load(), error_message=user_message_for_error(exc))
        if enabled:
            message = (
                "Automatic AI analysis turned on. Emails arriving from now on "
                "are analyzed; earlier ones are not (use Analyze for those)."
            )
        else:
            message = (
                "Automatic AI analysis turned off. New emails are still "
                "collected but not analyzed; Analyze still works on demand."
            )
            if cancelled:
                message += f" Cancelled {cancelled} waiting analysis(es)."
        return replace(self.load(), info_message=message)

    def set_ai_output_token_limit(self, value: int | None) -> SettingsViewState:
        """Save a new limit, or ``None`` to use the .env default again."""
        try:
            limit = self._executor.run(
                lambda: self._use_cases.set_ai_output_token_limit.execute(value)
            )
        except Exception as exc:
            return replace(self.load(), error_message=user_message_for_error(exc))
        message = (
            f"AI output token limit set to {limit.effective}."
            if limit.overridden
            else f"AI output token limit reset to the default ({limit.effective})."
        )
        return replace(
            self.load(),
            info_message=f"{message} It applies to the next analysis.",
        )

    def _load_monitoring_fields(self) -> _MonitoringFields:
        """Presentation-safe monitoring status — never includes credentials."""
        try:
            pubsub_connected = self._executor.run(
                lambda: self._use_cases.get_pubsub_connection_status.execute()
            )
        except Exception:
            pubsub_connected = False
        try:
            status = self._executor.run(
                lambda: self._use_cases.get_monitoring_status.execute()
            )
        except Exception as exc:
            return _MonitoringFields(
                status="ERROR",
                last_error=user_message_for_error(exc),
                pubsub_connected=pubsub_connected,
            )
        return _MonitoringFields(
            status=status.status,
            account_email=display_or_dash(status.account_email),
            watched_topics=(
                ", ".join(status.watched_topic_names)
                if status.watched_topic_names
                else "—"
            ),
            pubsub_project=display_or_dash(status.pubsub_project_id),
            pubsub_topic=display_or_dash(status.pubsub_topic),
            pubsub_subscription=display_or_dash(status.pubsub_subscription),
            watch_expiration=format_timestamp(status.watch_expiration),
            last_sync=format_timestamp(status.last_sync_at),
            last_notification=format_timestamp(status.last_notification_at),
            last_error=display_or_dash(status.last_error),
            pubsub_connected=pubsub_connected,
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
            return replace(
                state,
                gmail_account=account.email,
                busy=False,
                info_message=f"Connected as {account.email}",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def disconnect_gmail(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.disconnect_gmail.execute())
            self._labels = ()
            self._selected_label_id = None
            state = self.load()
            return replace(
                state,
                labels=(),
                selected_label_id=None,
                busy=False,
                info_message="Gmail disconnected.",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

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
            return replace(
                state,
                busy=False,
                info_message=f"Loaded {len(self._labels)} labels.",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

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
            return replace(state, error_message="Select a Gmail label first.")
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
            return replace(
                state,
                selected_topic_id=mapping.topic_id,
                info_message=(
                    f"Mapped label '{mapping.label_name or mapping.label_id}' "
                    f"to topic '{mapping.topic_name}'."
                ),
            )
        except Exception as exc:
            state = self.load()
            return replace(state, error_message=user_message_for_error(exc))

    # -- Real-time monitoring actions (Phase 10) -------------------------

    def connect_pubsub(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.connect_pubsub.execute())
            state = self.load()
            return replace(state, busy=False, info_message="Pub/Sub access authorized.")
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def disconnect_pubsub(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.disconnect_pubsub.execute())
            state = self.load()
            return replace(
                state, busy=False, info_message="Pub/Sub authorization removed."
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def start_monitoring(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.start_monitoring.execute())
            state = self.load()
            return replace(
                state,
                busy=False,
                info_message=f"Monitoring: {state.monitoring_status}.",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def stop_monitoring(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.stop_monitoring.execute())
            state = self.load()
            return replace(state, busy=False, info_message="Monitoring stopped.")
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def renew_watch(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.renew_gmail_watch.execute())
            state = self.load()
            return replace(state, busy=False, info_message="Gmail watch renewed.")
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    # -- Windows auto-start (Phase 13) ------------------------------------

    def enable_startup(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.enable_startup.execute())
            state = self.load()
            return replace(
                state,
                busy=False,
                info_message="InsightFlow AI will start with Windows.",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))

    def disable_startup(self) -> SettingsViewState:
        try:
            self._executor.run(lambda: self._use_cases.disable_startup.execute())
            state = self.load()
            return replace(
                state,
                busy=False,
                info_message="InsightFlow AI will no longer start with Windows.",
            )
        except Exception as exc:
            state = self.load()
            return replace(state, busy=False, error_message=user_message_for_error(exc))
