"""Diagnostics "AI providers" row tests (Phase 11 correction).

The row must be derived from the already-loaded ``AISettings`` and the
process-wide ``AIWorkerHandle`` — never from a network/AWS call.
"""

from __future__ import annotations

from pathlib import Path

from tests.fakes.ai import FakeAIProvider
from tests.fakes.gmail import FakeGmailAdapter
from tests.fakes.notifications import FakeNotificationPort
from tests.fakes.pubsub import FakePubSubAuthenticator, FakePubSubSubscriber
from tests.fakes.startup import FakeStartupRegistrationPort
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.use_cases import ApplicationUseCases, build_use_cases
from insightflow.configuration.diagnostics import RuntimeDiagnostics
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)
from insightflow.infrastructure.pubsub.message_parser import (
    parse_gmail_pubsub_notification,
)
from insightflow.presentation.viewmodels.diagnostics_view_model import (
    DiagnosticsViewModel,
)

_NOTIFICATIONS_SETTINGS = NotificationsSettings(enabled=True)

_PUBSUB_SETTINGS = PubSubSettings(
    project_id="test-project",
    topic="test-gmail-topic",
    subscription="test-gmail-subscription",
    history_batch_size=50,
    history_page_size=100,
    full_sync_max_messages=50,
    watch_renewal_margin_hours=24.0,
    pull_max_messages=10,
    idle_poll_seconds=5.0,
)

_DIAGNOSTICS = RuntimeDiagnostics(
    app_name="InsightFlow AI",
    app_version="0.1.0",
    python_version="3.13.0",
    operating_system="Windows 10 (AMD64)",
    environment="development",
    data_dir="C:\\data",
    log_dir="C:\\logs",
    database_dir="C:\\db",
    logging_level="INFO",
    logging_console_enabled=True,
    logging_file_enabled=True,
    logging_initialized=True,
    secret_store_backend="memory",
)


def _build_use_cases(ai_settings: AISettings) -> ApplicationUseCases:
    store = InMemoryStore()
    gmail = FakeGmailAdapter()
    return build_use_cases(
        store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
        gmail_messages=gmail,
        gmail_watch=gmail,
        gmail_history=gmail,
        pubsub_authenticator=FakePubSubAuthenticator(),
        pubsub_subscriber_factory=lambda: FakePubSubSubscriber(),
        parse_pubsub_notification=parse_gmail_pubsub_notification,
        pubsub_settings=_PUBSUB_SETTINGS,
        ai_provider=FakeAIProvider(),
        ai_settings=ai_settings,
        notification_port=FakeNotificationPort(),
        notifications_settings=_NOTIFICATIONS_SETTINGS,
        startup_registration_port=FakeStartupRegistrationPort(),
    )


def _ai_row(use_cases: ApplicationUseCases) -> str:
    vm = DiagnosticsViewModel(
        use_cases=use_cases,
        diagnostics=_DIAGNOSTICS,
        database_path=Path("C:\\db\\insightflow.db"),
    )
    state = vm.load()
    rows = dict(state.rows)
    return rows["AI providers"]


def test_ai_disabled_shows_disabled() -> None:
    use_cases = _build_use_cases(
        AISettings(
            enabled=False,
            automatic_analysis_enabled=True,
            provider="bedrock",
            region="us-east-2",
            model_id="global.anthropic.claude-opus-4-6-v1",
            timeout_seconds=30.0,
            max_retries=2,
            max_input_chars=12_000,
            max_output_tokens=1024,
            temperature=0.2,
            queue_max_size=100,
        )
    )
    assert _ai_row(use_cases) == "Disabled"


def test_ai_enabled_missing_model_id_shows_not_configured() -> None:
    use_cases = _build_use_cases(
        AISettings(
            enabled=True,
            automatic_analysis_enabled=True,
            provider="bedrock",
            region="us-east-2",
            model_id="",
            timeout_seconds=30.0,
            max_retries=2,
            max_input_chars=12_000,
            max_output_tokens=1024,
            temperature=0.2,
            queue_max_size=100,
        )
    )
    assert _ai_row(use_cases) == "Not configured"


def test_ai_enabled_and_configured_shows_enabled_regardless_of_worker_state() -> None:
    """Phase 13: the row must reflect ``AISettings`` only, never the local
    ``ai_worker_handle`` — that handle is always empty in the Desktop
    process (see ProcessRole), so it can never be used to report
    running/stopped without lying once monitoring lives in a separate
    Agent process. True either way the worker handle happens to be.
    """
    use_cases = _build_use_cases(
        AISettings(
            enabled=True,
            automatic_analysis_enabled=True,
            provider="bedrock",
            region="us-east-2",
            model_id="global.anthropic.claude-opus-4-6-v1",
            timeout_seconds=30.0,
            max_retries=2,
            max_input_chars=12_000,
            max_output_tokens=1024,
            temperature=0.2,
            queue_max_size=100,
        )
    )
    try:
        assert use_cases.ai_worker_handle.is_running
        assert _ai_row(use_cases) == "bedrock (enabled)"
    finally:
        use_cases.ai_worker_handle.stop(join_timeout_seconds=1.0)

    assert _ai_row(use_cases) == "bedrock (enabled)"


def test_ai_row_never_contains_secret_markers() -> None:
    use_cases = _build_use_cases(
        AISettings(
            enabled=True,
            automatic_analysis_enabled=True,
            provider="bedrock",
            region="us-east-2",
            model_id="global.anthropic.claude-opus-4-6-v1",
            timeout_seconds=30.0,
            max_retries=2,
            max_input_chars=12_000,
            max_output_tokens=1024,
            temperature=0.2,
            queue_max_size=100,
        )
    )
    try:
        vm = DiagnosticsViewModel(
            use_cases=use_cases,
            diagnostics=_DIAGNOSTICS,
            database_path=Path("C:\\db\\insightflow.db"),
        )
        state = vm.load()
        assert not state.contains_secret_values
    finally:
        use_cases.ai_worker_handle.stop(join_timeout_seconds=1.0)
