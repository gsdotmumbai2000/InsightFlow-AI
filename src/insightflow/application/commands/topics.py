"""Topic management use cases."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.mappers import topic_to_dto
from insightflow.application.dto.models import (
    CreateTopicRequest,
    TopicDto,
    UpdateTopicRequest,
)
from insightflow.application.exceptions import (
    AIProfileNotFoundError,
    ApplicationValidationError,
    DuplicateTopicError,
    TopicNotFoundError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import (
    AIProfileId,
    SourceConfiguration,
    SourceType,
    Topic,
    TopicId,
)


class CreateTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: CreateTopicRequest) -> TopicDto:
        with use_case_scope("CreateTopic"):

            def _run() -> TopicDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    source = SourceConfiguration(
                        source_type=SourceType(request.source_type),
                        source_id=request.source_id,
                        source_identifier=request.source_identifier,
                    )
                    existing = uow.topics.find_by_source_identifier(
                        source_id=source.source_id,
                        source_identifier=source.source_identifier,
                    )
                    if existing is not None:
                        raise DuplicateTopicError(
                            "A topic already exists for this source identifier."
                        )
                    profile_id = None
                    if request.ai_profile_id is not None:
                        profile_id = AIProfileId(request.ai_profile_id)
                        if uow.profiles.get(profile_id) is None:
                            raise AIProfileNotFoundError(
                                f"AI profile not found: {request.ai_profile_id}"
                            )
                    topic = Topic.create(
                        name=request.name,
                        source_configuration=source,
                        description=request.description,
                        ai_profile_id=profile_id,
                        notification_policy_ref=request.notification_policy_ref,
                    )
                    uow.topics.add(topic)
                    uow.commit()
                    return topic_to_dto(topic)

            return run_mutating(_run)


class UpdateTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: UpdateTopicRequest) -> TopicDto:
        with use_case_scope("UpdateTopic"):

            def _run() -> TopicDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    topic = uow.topics.get(TopicId(request.topic_id))
                    if topic is None:
                        raise TopicNotFoundError(f"Topic not found: {request.topic_id}")
                    if request.name is not None:
                        topic.name = _require_text(request.name, "name")
                    if request.description is not None:
                        topic.description = _require_text(
                            request.description, "description"
                        )
                    if request.clear_ai_profile:
                        topic.ai_profile_id = None
                    elif request.ai_profile_id is not None:
                        profile_id = AIProfileId(request.ai_profile_id)
                        if uow.profiles.get(profile_id) is None:
                            raise AIProfileNotFoundError(
                                f"AI profile not found: {request.ai_profile_id}"
                            )
                        topic.ai_profile_id = profile_id
                    if request.clear_notification_policy:
                        topic.notification_policy_ref = None
                    elif request.notification_policy_ref is not None:
                        topic.notification_policy_ref = _require_text(
                            request.notification_policy_ref,
                            "notification_policy_ref",
                        )
                    topic.updated_at = datetime.now(UTC)
                    uow.topics.update(topic)
                    uow.commit()
                    return topic_to_dto(topic)

            return run_mutating(_run)


class EnableTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        return _transition_topic(self._uow_factory, topic_id, "enable")


class DisableTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        return _transition_topic(self._uow_factory, topic_id, "disable")


class PauseTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        return _transition_topic(self._uow_factory, topic_id, "pause")


class ResumeTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        return _transition_topic(self._uow_factory, topic_id, "resume")


class GetTopicUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        with (
            use_case_scope("GetTopic"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            topic = uow.topics.get(TopicId(topic_id))
            if topic is None:
                raise TopicNotFoundError(f"Topic not found: {topic_id}")
            return topic_to_dto(topic)


class ListTopicsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, *, enabled_only: bool = False) -> list[TopicDto]:
        with (
            use_case_scope("ListTopics"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            topics = (
                uow.topics.list_enabled() if enabled_only else uow.topics.list_all()
            )
            return [topic_to_dto(topic) for topic in topics]


def _require_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ApplicationValidationError(f"{field_name} must not be empty")
    return cleaned


def _transition_topic(
    uow_factory: Callable[[], UnitOfWork],
    topic_id: str,
    action: str,
) -> TopicDto:
    with use_case_scope(f"{action.title()}Topic"):

        def _run() -> TopicDto:
            with unit_of_work_scope(uow_factory) as uow:
                topic = uow.topics.get(TopicId(topic_id))
                if topic is None:
                    raise TopicNotFoundError(f"Topic not found: {topic_id}")
                if action == "enable":
                    topic.enable()
                elif action == "disable":
                    topic.disable()
                elif action == "pause":
                    topic.pause()
                elif action == "resume":
                    topic.resume()
                else:
                    raise ApplicationValidationError(f"Unknown topic action: {action}")
                uow.topics.update(topic)
                uow.commit()
                return topic_to_dto(topic)

        return run_mutating(_run)
