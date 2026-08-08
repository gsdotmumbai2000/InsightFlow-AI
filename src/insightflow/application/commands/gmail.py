"""Gmail application use cases."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
    GmailLabelMappingDto,
    MapGmailLabelToTopicRequest,
)
from insightflow.application.dto.mappers import topic_to_dto
from insightflow.application.dto.models import TopicDto
from insightflow.application.exceptions import (
    ApplicationValidationError,
    DuplicateTopicError,
    TopicNotFoundError,
)
from insightflow.application.exceptions.gmail import GmailConnectionError
from insightflow.application.ports.gmail import GmailAuthenticator, GmailLabelProvider
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import SourceConfiguration, SourceType, Topic, TopicId


class ConnectGmailUseCase:
    def __init__(self, authenticator: GmailAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> GmailAccountDto:
        with use_case_scope("ConnectGmail"):
            return self._authenticator.connect()


class DisconnectGmailUseCase:
    def __init__(self, authenticator: GmailAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> None:
        with use_case_scope("DisconnectGmail"):
            self._authenticator.disconnect()


class GetGmailConnectionStatusUseCase:
    def __init__(self, authenticator: GmailAuthenticator) -> None:
        self._authenticator = authenticator

    def execute(self) -> GmailConnectionStatusDto:
        with use_case_scope("GetGmailConnectionStatus"):
            return self._authenticator.get_connection_status()


class ListGmailLabelsUseCase:
    def __init__(
        self,
        authenticator: GmailAuthenticator,
        labels: GmailLabelProvider,
    ) -> None:
        self._authenticator = authenticator
        self._labels = labels

    def execute(self) -> list[GmailLabelDto]:
        with use_case_scope("ListGmailLabels"):
            status = self._authenticator.get_connection_status()
            if status.status != "CONNECTED":
                raise GmailConnectionError(
                    status.message or "Gmail must be connected to list labels."
                )
            return self._labels.list_labels()


class MapGmailLabelToTopicUseCase:
    """Associate a Gmail label with a Topic via SourceConfiguration."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        authenticator: GmailAuthenticator,
    ) -> None:
        self._uow_factory = uow_factory
        self._authenticator = authenticator

    def execute(self, request: MapGmailLabelToTopicRequest) -> GmailLabelMappingDto:
        with use_case_scope("MapGmailLabelToTopic"):

            def _run() -> GmailLabelMappingDto:
                account = self._authenticator.get_account()
                if account is None:
                    raise GmailConnectionError("Gmail is not connected.")
                label_id = request.label_id.strip()
                if not label_id:
                    raise ApplicationValidationError("label_id must not be empty")

                source = SourceConfiguration(
                    source_type=SourceType.GMAIL,
                    source_id=account.account_id,
                    source_identifier=label_id,
                )
                with unit_of_work_scope(self._uow_factory) as uow:
                    existing = uow.topics.find_by_source_identifier(
                        source_id=source.source_id,
                        source_identifier=source.source_identifier,
                    )
                    if request.topic_id:
                        if (
                            existing is not None
                            and existing.id.value != request.topic_id
                        ):
                            raise DuplicateTopicError(
                                "Another topic already uses this Gmail label."
                            )
                        topic = uow.topics.get(TopicId(request.topic_id))
                        if topic is None:
                            raise TopicNotFoundError(
                                f"Topic not found: {request.topic_id}"
                            )
                        topic.source_configuration = source
                        if request.label_name:
                            topic.metadata["gmail_label_name"] = request.label_name
                        topic.updated_at = datetime.now(UTC)
                        uow.topics.update(topic)
                    else:
                        if existing is not None:
                            raise DuplicateTopicError(
                                "A topic already exists for this Gmail label."
                            )
                        name = (request.topic_name or "").strip()
                        if not name:
                            raise ApplicationValidationError(
                                "topic_name is required when creating a topic"
                            )
                        topic = Topic.create(
                            name=name,
                            source_configuration=source,
                            description=request.topic_description,
                        )
                        if request.label_name:
                            topic.metadata["gmail_label_name"] = request.label_name
                        uow.topics.add(topic)
                    uow.commit()
                    return GmailLabelMappingDto(
                        topic_id=topic.id.value,
                        topic_name=topic.name,
                        account_id=account.account_id,
                        label_id=label_id,
                        label_name=request.label_name,
                    )

            return run_mutating(_run)


class RemoveGmailLabelMappingUseCase:
    """Clear Gmail source binding from a topic (reverts to local GENERIC source)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, topic_id: str) -> TopicDto:
        with use_case_scope("RemoveGmailLabelMapping"):

            def _run() -> TopicDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    topic = uow.topics.get(TopicId(topic_id))
                    if topic is None:
                        raise TopicNotFoundError(f"Topic not found: {topic_id}")
                    topic.source_configuration = SourceConfiguration(
                        source_type=SourceType.GENERIC,
                        source_id="local",
                        source_identifier=f"manual-{uuid4()}",
                    )
                    topic.metadata.pop("gmail_label_name", None)
                    topic.updated_at = datetime.now(UTC)
                    uow.topics.update(topic)
                    uow.commit()
                    return topic_to_dto(topic)

            return run_mutating(_run)
