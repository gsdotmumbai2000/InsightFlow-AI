"""Application use-case registry."""

from __future__ import annotations

import queue
from collections.abc import Callable
from dataclasses import dataclass

from insightflow.application.commands.ai import (
    AnalyzeIntelligenceEventUseCase,
    GetAIAnalysisUseCase,
    ReprocessAIAnalysisUseCase,
)
from insightflow.application.commands.ai_profiles import (
    CreateAIProfileUseCase,
    DeleteAIProfileUseCase,
    GetAIProfileUseCase,
    ListAIProfilesUseCase,
    UpdateAIProfileUseCase,
)
from insightflow.application.commands.ai_settings import (
    GetAIAnalysisEnabledUseCase,
    GetAIOutputTokenLimitUseCase,
    SetAIAnalysisEnabledUseCase,
    SetAIOutputTokenLimitUseCase,
)
from insightflow.application.commands.events import (
    ClearAllIntelligenceEventsUseCase,
    CreateIntelligenceEventUseCase,
    GetIntelligenceEventUseCase,
    ListEventsByTopicUseCase,
    ListRecentIntelligenceEventsUseCase,
    MarkEventCompletedUseCase,
    MarkEventFailedUseCase,
    MarkEventIgnoredUseCase,
    MarkEventProcessingUseCase,
)
from insightflow.application.commands.gmail import (
    ConnectGmailUseCase,
    DisconnectGmailUseCase,
    GetGmailConnectionStatusUseCase,
    IngestTopicMessagesUseCase,
    ListGmailLabelsUseCase,
    MapGmailLabelToTopicUseCase,
    RemoveGmailLabelMappingUseCase,
    RetrieveTopicMessagesUseCase,
)
from insightflow.application.commands.monitoring import (
    ConnectPubSubUseCase,
    DisconnectPubSubUseCase,
    GetMonitoringStatusUseCase,
    GetPubSubConnectionStatusUseCase,
    RenewGmailWatchUseCase,
    RequestStartMonitoringUseCase,
    RequestStopMonitoringUseCase,
    StartMonitoringCommand,
    StartMonitoringUseCase,
    StopMonitoringCommand,
    StopMonitoringUseCase,
)
from insightflow.application.commands.notifications import (
    ClearAllNotificationsUseCase,
    GetNotificationUseCase,
    ListRecentNotificationsUseCase,
    MarkNotificationDismissedUseCase,
    MarkNotificationDisplayedUseCase,
)
from insightflow.application.commands.startup import (
    DisableStartupUseCase,
    EnableStartupUseCase,
    GetStartupRegistrationStatusUseCase,
)
from insightflow.application.commands.topics import (
    CreateTopicUseCase,
    DisableTopicUseCase,
    EnableTopicUseCase,
    GetTopicUseCase,
    ListTopicsUseCase,
    PauseTopicUseCase,
    ResumeTopicUseCase,
    UpdateTopicUseCase,
)
from insightflow.application.dto.ai import AIAnalysisJob
from insightflow.application.dto.monitoring import PubSubNotificationDto
from insightflow.application.ports.ai import AIProvider
from insightflow.application.ports.gmail import (
    GmailAuthenticator,
    GmailHistoryProvider,
    GmailLabelProvider,
    GmailMessageProvider,
    GmailWatchProvider,
)
from insightflow.application.ports.notifications import NotificationPort
from insightflow.application.ports.pubsub import PubSubAuthenticator, PubSubSubscriber
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.application.ports.startup import StartupRegistrationPort
from insightflow.application.process_role import ProcessRole
from insightflow.application.queries.attachments import (
    GetAttachmentUseCase,
    ListEventAttachmentsUseCase,
)
from insightflow.application.queries.dashboard import GetDashboardSummaryUseCase
from insightflow.application.queries.stories import (
    GetStoryEventsUseCase,
    GetStoryUseCase,
    ListStoriesUseCase,
)
from insightflow.application.services.ai_dispatch import (
    AIAnalysisDispatcher,
    ai_job_should_run,
    find_pending_ai_jobs,
    mark_ai_job_failed,
)
from insightflow.application.services.ai_prompt_builder import AIPromptBuilder
from insightflow.application.services.ai_response_validator import (
    AIResponseValidator,
)
from insightflow.application.services.ai_worker import AIWorker
from insightflow.application.services.ai_worker_handle import AIWorkerHandle
from insightflow.application.services.gmail_full_sync import GmailFullSyncService
from insightflow.application.services.gmail_history_sync import (
    GmailHistorySyncService,
)
from insightflow.application.services.gmail_pubsub_processor import (
    GmailPubSubNotificationProcessor,
)
from insightflow.application.services.gmail_watch_lifecycle import (
    GmailWatchLifecycleService,
)
from insightflow.application.services.monitoring_events import (
    MonitoringEventBroadcaster,
)
from insightflow.application.services.monitoring_reconciler import (
    MonitoringDesiredStateReconciler,
)
from insightflow.application.services.monitoring_reconciler_handle import (
    MonitoringReconcilerHandle,
)
from insightflow.application.services.monitoring_worker_handle import (
    MonitoringWorkerHandle,
)
from insightflow.application.services.notification_dispatch import (
    ToastNotificationDispatcher,
)
from insightflow.configuration.models import (
    AISettings,
    NotificationsSettings,
    PubSubSettings,
)


@dataclass(slots=True)
class ApplicationUseCases:
    """Use cases wired by the composition root."""

    create_topic: CreateTopicUseCase
    update_topic: UpdateTopicUseCase
    enable_topic: EnableTopicUseCase
    disable_topic: DisableTopicUseCase
    pause_topic: PauseTopicUseCase
    resume_topic: ResumeTopicUseCase
    get_topic: GetTopicUseCase
    list_topics: ListTopicsUseCase
    create_intelligence_event: CreateIntelligenceEventUseCase
    clear_all_intelligence_events: ClearAllIntelligenceEventsUseCase
    get_intelligence_event: GetIntelligenceEventUseCase
    list_recent_intelligence_events: ListRecentIntelligenceEventsUseCase
    list_events_by_topic: ListEventsByTopicUseCase
    mark_event_processing: MarkEventProcessingUseCase
    mark_event_completed: MarkEventCompletedUseCase
    mark_event_failed: MarkEventFailedUseCase
    mark_event_ignored: MarkEventIgnoredUseCase
    get_ai_analysis: GetAIAnalysisUseCase
    reprocess_ai_analysis: ReprocessAIAnalysisUseCase
    create_ai_profile: CreateAIProfileUseCase
    update_ai_profile: UpdateAIProfileUseCase
    delete_ai_profile: DeleteAIProfileUseCase
    get_ai_profile: GetAIProfileUseCase
    list_ai_profiles: ListAIProfilesUseCase
    get_notification: GetNotificationUseCase
    clear_all_notifications: ClearAllNotificationsUseCase
    list_recent_notifications: ListRecentNotificationsUseCase
    mark_notification_displayed: MarkNotificationDisplayedUseCase
    mark_notification_dismissed: MarkNotificationDismissedUseCase
    get_attachment: GetAttachmentUseCase
    list_event_attachments: ListEventAttachmentsUseCase
    get_story: GetStoryUseCase
    list_stories: ListStoriesUseCase
    get_story_events: GetStoryEventsUseCase
    get_dashboard_summary: GetDashboardSummaryUseCase
    connect_gmail: ConnectGmailUseCase
    disconnect_gmail: DisconnectGmailUseCase
    get_gmail_connection_status: GetGmailConnectionStatusUseCase
    list_gmail_labels: ListGmailLabelsUseCase
    map_gmail_label_to_topic: MapGmailLabelToTopicUseCase
    remove_gmail_label_mapping: RemoveGmailLabelMappingUseCase
    retrieve_topic_messages: RetrieveTopicMessagesUseCase
    ingest_topic_messages: IngestTopicMessagesUseCase
    connect_pubsub: ConnectPubSubUseCase
    disconnect_pubsub: DisconnectPubSubUseCase
    get_pubsub_connection_status: GetPubSubConnectionStatusUseCase
    get_monitoring_status: GetMonitoringStatusUseCase
    start_monitoring: StartMonitoringCommand
    stop_monitoring: StopMonitoringCommand
    renew_gmail_watch: RenewGmailWatchUseCase
    monitoring_worker_handle: MonitoringWorkerHandle
    monitoring_reconciler_handle: MonitoringReconcilerHandle
    monitoring_event_broadcaster: MonitoringEventBroadcaster
    analyze_intelligence_event: AnalyzeIntelligenceEventUseCase
    ai_worker_handle: AIWorkerHandle
    ai_settings: AISettings
    get_ai_output_token_limit: GetAIOutputTokenLimitUseCase
    set_ai_output_token_limit: SetAIOutputTokenLimitUseCase
    get_ai_analysis_enabled: GetAIAnalysisEnabledUseCase
    set_ai_analysis_enabled: SetAIAnalysisEnabledUseCase
    notifications_settings: NotificationsSettings
    get_startup_registration_status: GetStartupRegistrationStatusUseCase
    enable_startup: EnableStartupUseCase
    disable_startup: DisableStartupUseCase


def build_use_cases(
    uow_factory: Callable[[], UnitOfWork],
    *,
    gmail_authenticator: GmailAuthenticator,
    gmail_labels: GmailLabelProvider,
    gmail_messages: GmailMessageProvider,
    gmail_watch: GmailWatchProvider,
    gmail_history: GmailHistoryProvider,
    pubsub_authenticator: PubSubAuthenticator,
    pubsub_subscriber_factory: Callable[[], PubSubSubscriber],
    parse_pubsub_notification: Callable[[bytes], PubSubNotificationDto | None],
    pubsub_settings: PubSubSettings,
    ai_provider: AIProvider,
    ai_settings: AISettings,
    notification_port: NotificationPort,
    notifications_settings: NotificationsSettings,
    startup_registration_port: StartupRegistrationPort,
    role: ProcessRole = ProcessRole.AGENT,
) -> ApplicationUseCases:
    """Construct use cases with explicit dependency injection.

    ``role`` (Phase 13) decides whether this process owns
    ``GmailMonitoringWorker``/``AIWorker`` (``ProcessRole.AGENT``, the
    default — preserves the pre-Phase-13 behavior every existing caller
    relies on) or is a read-mostly client that only records desired state
    (``ProcessRole.DESKTOP``). See ``bootstrap.agent`` and
    ``bootstrap.startup`` for the two composition roots.
    """
    monitoring_event_broadcaster = MonitoringEventBroadcaster()

    ai_job_queue: queue.Queue[AIAnalysisJob] = queue.Queue(
        maxsize=ai_settings.queue_max_size
    )

    def _enqueue_ai_job(job: AIAnalysisJob) -> None:
        # Only the Agent runs AIWorker. A Desktop job put on this queue would
        # never be drained, so the Desktop relies solely on the event being
        # persisted as AI_PROCESSING, which the Agent's worker scans for.
        if role is ProcessRole.AGENT:
            ai_job_queue.put_nowait(job)

    analyze_intelligence_event = AnalyzeIntelligenceEventUseCase(
        uow_factory,
        ai_provider,
        AIPromptBuilder(max_input_chars=ai_settings.max_input_chars),
        AIResponseValidator(),
        monitoring_event_broadcaster,
        provider_name=ai_settings.provider,
        model_id=ai_settings.model_id,
        max_output_tokens=ai_settings.max_output_tokens,
        temperature=ai_settings.temperature,
    )
    ai_dispatcher = AIAnalysisDispatcher(
        uow_factory,
        _enqueue_ai_job,
        enabled=ai_settings.enabled and ai_settings.automatic_analysis_enabled,
    )

    create_intelligence_event = CreateIntelligenceEventUseCase(uow_factory)
    retrieve_topic_messages = RetrieveTopicMessagesUseCase(
        uow_factory, gmail_authenticator, gmail_messages
    )
    ingest_topic_messages = IngestTopicMessagesUseCase(
        uow_factory,
        retrieve_topic_messages,
        create_intelligence_event,
        on_event_created=ai_dispatcher.dispatch,
    )

    toast_dispatcher = ToastNotificationDispatcher(
        uow_factory,
        notification_port,
        enabled=notifications_settings.enabled,
    )

    watch_lifecycle = GmailWatchLifecycleService(
        uow_factory,
        gmail_watch,
        pubsub_project_id=pubsub_settings.project_id,
        pubsub_topic_name=pubsub_settings.topic,
        pubsub_subscription=pubsub_settings.subscription,
        on_event=monitoring_event_broadcaster.notify,
    )
    history_sync = GmailHistorySyncService(
        uow_factory,
        gmail_history,
        gmail_messages,
        ingest_topic_messages,
        batch_size=pubsub_settings.history_batch_size,
        page_size=pubsub_settings.history_page_size,
        on_event_created=toast_dispatcher.dispatch,
    )
    full_sync = GmailFullSyncService(
        uow_factory,
        ingest_topic_messages,
        max_messages_per_topic=pubsub_settings.full_sync_max_messages,
        on_event_created=toast_dispatcher.dispatch,
    )
    pubsub_processor = GmailPubSubNotificationProcessor(
        uow_factory,
        history_sync,
        full_sync,
        watch_lifecycle,
        on_event=monitoring_event_broadcaster.notify,
    )
    monitoring_worker_handle = MonitoringWorkerHandle()
    get_monitoring_status = GetMonitoringStatusUseCase(
        uow_factory,
        gmail_authenticator,
        monitoring_worker_handle,
        reconcile_worker_liveness=role is ProcessRole.AGENT,
    )

    ai_worker = AIWorker(
        job_queue=ai_job_queue,
        analyze=analyze_intelligence_event,
        pending_jobs=lambda: find_pending_ai_jobs(uow_factory),
        on_job_failed=lambda job: mark_ai_job_failed(uow_factory, job),
        should_run=lambda job: ai_job_should_run(uow_factory, job),
    )
    ai_worker_handle = AIWorkerHandle()
    if role is ProcessRole.AGENT and ai_settings.enabled:
        ai_worker.start()
        ai_worker_handle.set(ai_worker)

    monitoring_reconciler_handle = MonitoringReconcilerHandle()
    start_monitoring: StartMonitoringCommand
    stop_monitoring: StopMonitoringCommand
    if role is ProcessRole.AGENT:
        agent_start_monitoring = StartMonitoringUseCase(
            uow_factory,
            gmail_authenticator,
            pubsub_authenticator,
            watch_lifecycle,
            full_sync,
            pubsub_processor,
            pubsub_subscriber_factory,
            parse_pubsub_notification,
            monitoring_worker_handle,
            get_monitoring_status,
            pull_max_messages=pubsub_settings.pull_max_messages,
            idle_poll_seconds=pubsub_settings.idle_poll_seconds,
            watch_renewal_margin_hours=pubsub_settings.watch_renewal_margin_hours,
        )
        agent_stop_monitoring = StopMonitoringUseCase(
            gmail_authenticator,
            watch_lifecycle,
            monitoring_worker_handle,
            get_monitoring_status,
            uow_factory,
        )
        start_monitoring = agent_start_monitoring
        stop_monitoring = agent_stop_monitoring
        reconciler = MonitoringDesiredStateReconciler(
            uow_factory=uow_factory,
            gmail_authenticator=gmail_authenticator,
            worker_handle=monitoring_worker_handle,
            start=agent_start_monitoring,
            stop=agent_stop_monitoring,
            refresh_status=get_monitoring_status.execute,
            poll_seconds=pubsub_settings.idle_poll_seconds,
        )
        # Constructed and attached here so it's always available on the
        # handle, but deliberately not started — see
        # MonitoringReconcilerHandle.start().
        monitoring_reconciler_handle.set(reconciler)
    else:
        start_monitoring = RequestStartMonitoringUseCase(
            uow_factory,
            gmail_authenticator,
            pubsub_authenticator,
            get_monitoring_status,
        )
        stop_monitoring = RequestStopMonitoringUseCase(
            uow_factory, gmail_authenticator, get_monitoring_status
        )

    return ApplicationUseCases(
        create_topic=CreateTopicUseCase(uow_factory),
        update_topic=UpdateTopicUseCase(uow_factory),
        enable_topic=EnableTopicUseCase(uow_factory),
        disable_topic=DisableTopicUseCase(uow_factory),
        pause_topic=PauseTopicUseCase(uow_factory),
        resume_topic=ResumeTopicUseCase(uow_factory),
        get_topic=GetTopicUseCase(uow_factory),
        list_topics=ListTopicsUseCase(uow_factory),
        create_intelligence_event=create_intelligence_event,
        get_intelligence_event=GetIntelligenceEventUseCase(uow_factory),
        list_recent_intelligence_events=ListRecentIntelligenceEventsUseCase(
            uow_factory
        ),
        list_events_by_topic=ListEventsByTopicUseCase(uow_factory),
        mark_event_processing=MarkEventProcessingUseCase(uow_factory),
        mark_event_completed=MarkEventCompletedUseCase(uow_factory),
        mark_event_failed=MarkEventFailedUseCase(uow_factory),
        mark_event_ignored=MarkEventIgnoredUseCase(uow_factory),
        get_ai_analysis=GetAIAnalysisUseCase(uow_factory),
        reprocess_ai_analysis=ReprocessAIAnalysisUseCase(
            uow_factory, _enqueue_ai_job, ai_enabled=ai_settings.enabled
        ),
        create_ai_profile=CreateAIProfileUseCase(uow_factory),
        update_ai_profile=UpdateAIProfileUseCase(uow_factory),
        delete_ai_profile=DeleteAIProfileUseCase(uow_factory),
        get_ai_profile=GetAIProfileUseCase(uow_factory),
        list_ai_profiles=ListAIProfilesUseCase(uow_factory),
        get_notification=GetNotificationUseCase(uow_factory),
        clear_all_notifications=ClearAllNotificationsUseCase(uow_factory),
        clear_all_intelligence_events=ClearAllIntelligenceEventsUseCase(uow_factory),
        list_recent_notifications=ListRecentNotificationsUseCase(uow_factory),
        mark_notification_displayed=MarkNotificationDisplayedUseCase(uow_factory),
        mark_notification_dismissed=MarkNotificationDismissedUseCase(uow_factory),
        get_attachment=GetAttachmentUseCase(uow_factory),
        list_event_attachments=ListEventAttachmentsUseCase(uow_factory),
        get_story=GetStoryUseCase(uow_factory),
        list_stories=ListStoriesUseCase(uow_factory),
        get_story_events=GetStoryEventsUseCase(uow_factory),
        get_dashboard_summary=GetDashboardSummaryUseCase(
            uow_factory, get_monitoring_status
        ),
        connect_gmail=ConnectGmailUseCase(gmail_authenticator),
        disconnect_gmail=DisconnectGmailUseCase(
            gmail_authenticator, monitoring_worker_handle
        ),
        get_gmail_connection_status=GetGmailConnectionStatusUseCase(
            gmail_authenticator
        ),
        list_gmail_labels=ListGmailLabelsUseCase(gmail_authenticator, gmail_labels),
        map_gmail_label_to_topic=MapGmailLabelToTopicUseCase(
            uow_factory, gmail_authenticator
        ),
        remove_gmail_label_mapping=RemoveGmailLabelMappingUseCase(uow_factory),
        retrieve_topic_messages=retrieve_topic_messages,
        ingest_topic_messages=ingest_topic_messages,
        connect_pubsub=ConnectPubSubUseCase(pubsub_authenticator),
        disconnect_pubsub=DisconnectPubSubUseCase(pubsub_authenticator),
        get_pubsub_connection_status=GetPubSubConnectionStatusUseCase(
            pubsub_authenticator
        ),
        get_monitoring_status=get_monitoring_status,
        start_monitoring=start_monitoring,
        stop_monitoring=stop_monitoring,
        renew_gmail_watch=RenewGmailWatchUseCase(
            gmail_authenticator, watch_lifecycle, get_monitoring_status
        ),
        monitoring_worker_handle=monitoring_worker_handle,
        monitoring_reconciler_handle=monitoring_reconciler_handle,
        monitoring_event_broadcaster=monitoring_event_broadcaster,
        analyze_intelligence_event=analyze_intelligence_event,
        ai_worker_handle=ai_worker_handle,
        ai_settings=ai_settings,
        get_ai_output_token_limit=GetAIOutputTokenLimitUseCase(
            uow_factory, configured_default=ai_settings.max_output_tokens
        ),
        set_ai_output_token_limit=SetAIOutputTokenLimitUseCase(
            uow_factory, configured_default=ai_settings.max_output_tokens
        ),
        get_ai_analysis_enabled=GetAIAnalysisEnabledUseCase(uow_factory),
        set_ai_analysis_enabled=SetAIAnalysisEnabledUseCase(uow_factory),
        notifications_settings=notifications_settings,
        get_startup_registration_status=GetStartupRegistrationStatusUseCase(
            startup_registration_port
        ),
        enable_startup=EnableStartupUseCase(startup_registration_port),
        disable_startup=DisableStartupUseCase(startup_registration_port),
    )
