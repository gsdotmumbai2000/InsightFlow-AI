"""Application DTO package."""

from __future__ import annotations

from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
    GmailLabelMappingDto,
    MapGmailLabelToTopicRequest,
)
from insightflow.application.dto.models import (
    AIAnalysisDto,
    AttachmentDto,
    CreateIntelligenceEventRequest,
    CreateTopicRequest,
    DashboardSummaryDto,
    IntelligenceEventDto,
    MarketImpactDto,
    NotificationDto,
    ReprocessAIRequest,
    ReprocessAIResult,
    SourceConfigurationDto,
    SourceReferenceDto,
    StoryDto,
    TopicDto,
    UpdateTopicRequest,
)

__all__ = [
    "AIAnalysisDto",
    "AttachmentDto",
    "CreateIntelligenceEventRequest",
    "CreateTopicRequest",
    "DashboardSummaryDto",
    "GmailAccountDto",
    "GmailConnectionStatusDto",
    "GmailLabelDto",
    "GmailLabelMappingDto",
    "IntelligenceEventDto",
    "MapGmailLabelToTopicRequest",
    "MarketImpactDto",
    "NotificationDto",
    "ReprocessAIRequest",
    "ReprocessAIResult",
    "SourceConfigurationDto",
    "SourceReferenceDto",
    "StoryDto",
    "TopicDto",
    "UpdateTopicRequest",
]
