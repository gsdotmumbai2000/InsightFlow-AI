"""AI profile management use cases.

An ``AIProfile`` represents topic-specific analysis intent (what to look
for and how to interpret it) — not provider/model configuration, which
remains controlled by ``AISettings``. This module creates, lists, and edits
profiles; editing the instructions starts a new profile version (see
``AIProfile.revise``). Topic assignment reuses ``UpdateTopicUseCase``.
"""

from __future__ import annotations

from collections.abc import Callable

from insightflow.application._support import (
    run_mutating,
    unit_of_work_scope,
    use_case_scope,
)
from insightflow.application.dto.mappers import profile_to_dto
from insightflow.application.dto.models import (
    AIProfileDto,
    CreateAIProfileRequest,
    UpdateAIProfileRequest,
)
from insightflow.application.exceptions import (
    AIProfileNotFoundError,
    ApplicationValidationError,
)
from insightflow.application.ports.repositories import UnitOfWork
from insightflow.domain import AIOutputStyle, AIProfile, AIProfileId


class CreateAIProfileUseCase:
    """Creates one AI profile via the existing ``AIProfileRepository``."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: CreateAIProfileRequest) -> AIProfileDto:
        with use_case_scope("CreateAIProfile"):

            def _run() -> AIProfileDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    profile = AIProfile.create(
                        name=request.name,
                        instructions=request.instructions,
                        output_schema_version=request.output_schema_version,
                        description=request.description,
                        output_style=_parse_output_style(request.output_style),
                    )
                    uow.profiles.add(profile)
                    uow.commit()
                    return profile_to_dto(profile)

            return run_mutating(_run)


class UpdateAIProfileUseCase:
    """Edits an AI profile's name, description, and instructions."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, request: UpdateAIProfileRequest) -> AIProfileDto:
        with use_case_scope("UpdateAIProfile"):

            def _run() -> AIProfileDto:
                with unit_of_work_scope(self._uow_factory) as uow:
                    profile = uow.profiles.get(AIProfileId(request.profile_id))
                    if profile is None:
                        raise AIProfileNotFoundError(
                            f"AI profile not found: {request.profile_id}"
                        )
                    profile.revise(
                        name=request.name,
                        description=request.description,
                        instructions=request.instructions,
                        output_style=(
                            _parse_output_style(request.output_style)
                            if request.output_style is not None
                            else None
                        ),
                    )
                    uow.profiles.update(profile)
                    uow.commit()
                    return profile_to_dto(profile)

            return run_mutating(_run)


class DeleteAIProfileUseCase:
    """Deletes an AI profile so it can be re-created from scratch.

    Topics using it go back to "no AI profile". Analyses it already produced
    are kept (they still show on their events); the profile simply no longer
    appears anywhere, and a new profile may reuse its name.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, profile_id: str) -> None:
        with use_case_scope("DeleteAIProfile"):

            def _run() -> None:
                with unit_of_work_scope(self._uow_factory) as uow:
                    target = AIProfileId(profile_id)
                    if uow.profiles.get(target) is None:
                        raise AIProfileNotFoundError(
                            f"AI profile not found: {profile_id}"
                        )
                    for topic in uow.topics.list_all():
                        if topic.ai_profile_id == target:
                            topic.ai_profile_id = None
                            uow.topics.update(topic)
                    uow.profiles.delete(target)
                    uow.commit()

            run_mutating(_run)


class GetAIProfileUseCase:
    """Returns one AI profile, e.g. to pre-fill the edit dialog."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self, profile_id: str) -> AIProfileDto:
        with (
            use_case_scope("GetAIProfile"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            profile = uow.profiles.get(AIProfileId(profile_id))
            if profile is None:
                raise AIProfileNotFoundError(f"AI profile not found: {profile_id}")
            return profile_to_dto(profile)


def _parse_output_style(raw: str) -> AIOutputStyle:
    try:
        return AIOutputStyle(raw.strip().upper())
    except ValueError as exc:
        raise ApplicationValidationError(f"Unknown AI output style: {raw!r}.") from exc


class ListAIProfilesUseCase:
    """Lists every AI profile, for Topic-assignment pickers."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def execute(self) -> list[AIProfileDto]:
        with (
            use_case_scope("ListAIProfiles"),
            unit_of_work_scope(self._uow_factory) as uow,
        ):
            return [profile_to_dto(profile) for profile in uow.profiles.list_all()]
