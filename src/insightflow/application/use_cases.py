"""Application use-case registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from insightflow.application.commands.ai import (
    GetAIAnalysisUseCase,
    ReprocessAIAnalysisUseCase,
)
from insightflow.application.commands.events import (
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
    ListGmailLabelsUseCase,
    MapGmailLabelToTopicUseCase,
    RemoveGmailLabelMappingUseCase,
)
from insightflow.application.commands.notifications import (
    GetNotificationUseCase,
    ListRecentNotificationsUseCase,
    MarkNotificationDismissedUseCase,
    MarkNotificationDisplayedUseCase,
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
from insightflow.application.ports.gmail import GmailAuthenticator, GmailLabelProvider
from insightflow.application.ports.repositories import UnitOfWork
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
    get_intelligence_event: GetIntelligenceEventUseCase
    list_recent_intelligence_events: ListRecentIntelligenceEventsUseCase
    list_events_by_topic: ListEventsByTopicUseCase
    mark_event_processing: MarkEventProcessingUseCase
    mark_event_completed: MarkEventCompletedUseCase
    mark_event_failed: MarkEventFailedUseCase
    mark_event_ignored: MarkEventIgnoredUseCase
    get_ai_analysis: GetAIAnalysisUseCase
    reprocess_ai_analysis: ReprocessAIAnalysisUseCase
    get_notification: GetNotificationUseCase
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


def build_use_cases(
    uow_factory: Callable[[], UnitOfWork],
    *,
    gmail_authenticator: GmailAuthenticator,
    gmail_labels: GmailLabelProvider,
) -> ApplicationUseCases:
    """Construct use cases with explicit dependency injection."""
    return ApplicationUseCases(
        create_topic=CreateTopicUseCase(uow_factory),
        update_topic=UpdateTopicUseCase(uow_factory),
        enable_topic=EnableTopicUseCase(uow_factory),
        disable_topic=DisableTopicUseCase(uow_factory),
        pause_topic=PauseTopicUseCase(uow_factory),
        resume_topic=ResumeTopicUseCase(uow_factory),
        get_topic=GetTopicUseCase(uow_factory),
        list_topics=ListTopicsUseCase(uow_factory),
        create_intelligence_event=CreateIntelligenceEventUseCase(uow_factory),
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
        reprocess_ai_analysis=ReprocessAIAnalysisUseCase(uow_factory),
        get_notification=GetNotificationUseCase(uow_factory),
        list_recent_notifications=ListRecentNotificationsUseCase(uow_factory),
        mark_notification_displayed=MarkNotificationDisplayedUseCase(uow_factory),
        mark_notification_dismissed=MarkNotificationDismissedUseCase(uow_factory),
        get_attachment=GetAttachmentUseCase(uow_factory),
        list_event_attachments=ListEventAttachmentsUseCase(uow_factory),
        get_story=GetStoryUseCase(uow_factory),
        list_stories=ListStoriesUseCase(uow_factory),
        get_story_events=GetStoryEventsUseCase(uow_factory),
        get_dashboard_summary=GetDashboardSummaryUseCase(uow_factory),
        connect_gmail=ConnectGmailUseCase(gmail_authenticator),
        disconnect_gmail=DisconnectGmailUseCase(gmail_authenticator),
        get_gmail_connection_status=GetGmailConnectionStatusUseCase(
            gmail_authenticator
        ),
        list_gmail_labels=ListGmailLabelsUseCase(gmail_authenticator, gmail_labels),
        map_gmail_label_to_topic=MapGmailLabelToTopicUseCase(
            uow_factory, gmail_authenticator
        ),
        remove_gmail_label_mapping=RemoveGmailLabelMappingUseCase(uow_factory),
    )
