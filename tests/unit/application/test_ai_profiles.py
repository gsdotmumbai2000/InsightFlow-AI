"""AI profile creation/listing and Topic-assignment use-case tests."""

from __future__ import annotations

import pytest

from insightflow.application.dto.models import (
    CreateAIProfileRequest,
    CreateTopicRequest,
    UpdateAIProfileRequest,
    UpdateTopicRequest,
)
from insightflow.application.exceptions import (
    AIProfileNotFoundError,
    ApplicationValidationError,
)
from insightflow.application.use_cases import ApplicationUseCases


def _profile_request(**overrides: object) -> CreateAIProfileRequest:
    payload: dict[str, object] = {
        "name": "US Market Impact",
        "instructions": "Analyze US market-moving news.",
        "output_schema_version": "v1",
    }
    payload.update(overrides)
    return CreateAIProfileRequest(**payload)  # type: ignore[arg-type]


def _topic_request(**overrides: object) -> CreateTopicRequest:
    payload: dict[str, object] = {
        "name": "TRUMP",
        "source_type": "GMAIL",
        "source_id": "acct-1",
        "source_identifier": "Label_TRUMP",
    }
    payload.update(overrides)
    return CreateTopicRequest(**payload)  # type: ignore[arg-type]


def test_create_ai_profile_persists_with_defaults(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(_profile_request())
    assert created.name == "US Market Impact"
    assert created.instructions == "Analyze US market-moving news."
    assert created.output_schema_version == "v1"
    assert created.version == 1
    assert created.enabled is True
    assert created.description is None


def test_create_ai_profile_with_description(use_cases: ApplicationUseCases) -> None:
    created = use_cases.create_ai_profile.execute(
        _profile_request(description="Test description")
    )
    assert created.description == "Test description"


def test_create_ai_profile_rejects_empty_name(
    use_cases: ApplicationUseCases,
) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.create_ai_profile.execute(_profile_request(name=""))


def test_create_ai_profile_rejects_empty_instructions(
    use_cases: ApplicationUseCases,
) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.create_ai_profile.execute(_profile_request(instructions=""))


def test_create_ai_profile_rejects_empty_output_schema_version(
    use_cases: ApplicationUseCases,
) -> None:
    with pytest.raises(ApplicationValidationError):
        use_cases.create_ai_profile.execute(_profile_request(output_schema_version=""))


def test_created_profile_is_persisted_through_repository(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(_profile_request())
    listed = use_cases.list_ai_profiles.execute()
    assert [profile.id for profile in listed] == [created.id]


def test_list_ai_profiles_empty_by_default(use_cases: ApplicationUseCases) -> None:
    assert use_cases.list_ai_profiles.execute() == []


def test_list_ai_profiles_returns_all_created(
    use_cases: ApplicationUseCases,
) -> None:
    first = use_cases.create_ai_profile.execute(_profile_request(name="First"))
    second = use_cases.create_ai_profile.execute(_profile_request(name="Second"))
    listed = use_cases.list_ai_profiles.execute()
    assert {profile.id for profile in listed} == {first.id, second.id}


def test_attach_existing_profile_to_topic(use_cases: ApplicationUseCases) -> None:
    profile = use_cases.create_ai_profile.execute(_profile_request())
    topic = use_cases.create_topic.execute(_topic_request())
    assert topic.ai_profile_id is None

    updated = use_cases.update_topic.execute(
        UpdateTopicRequest(topic_id=topic.id, ai_profile_id=profile.id)
    )
    assert updated.ai_profile_id == profile.id

    reloaded = use_cases.get_topic.execute(topic.id)
    assert reloaded.ai_profile_id == profile.id


def test_attach_nonexistent_profile_raises_via_existing_update_topic_use_case(
    use_cases: ApplicationUseCases,
) -> None:
    topic = use_cases.create_topic.execute(_topic_request())
    with pytest.raises(AIProfileNotFoundError):
        use_cases.update_topic.execute(
            UpdateTopicRequest(topic_id=topic.id, ai_profile_id="missing-profile-id")
        )


def test_update_ai_profile_new_instructions_start_a_new_version(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(_profile_request())

    updated = use_cases.update_ai_profile.execute(
        UpdateAIProfileRequest(
            profile_id=created.id,
            name="US Market Impact",
            instructions="Focus on Federal Reserve decisions.",
            description="Edited",
        )
    )

    assert updated.version == 2
    assert updated.instructions == "Focus on Federal Reserve decisions."
    assert updated.description == "Edited"
    reloaded = use_cases.get_ai_profile.execute(created.id)
    assert reloaded.version == 2
    assert reloaded.instructions == "Focus on Federal Reserve decisions."


def test_update_ai_profile_rename_keeps_version(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(_profile_request())

    updated = use_cases.update_ai_profile.execute(
        UpdateAIProfileRequest(
            profile_id=created.id,
            name="Renamed",
            instructions=created.instructions,
        )
    )

    assert updated.name == "Renamed"
    assert updated.version == 1


def test_update_ai_profile_rejects_empty_instructions(
    use_cases: ApplicationUseCases,
) -> None:
    created = use_cases.create_ai_profile.execute(_profile_request())
    with pytest.raises(ApplicationValidationError):
        use_cases.update_ai_profile.execute(
            UpdateAIProfileRequest(
                profile_id=created.id, name="US Market Impact", instructions="  "
            )
        )


def test_update_unknown_ai_profile_raises(use_cases: ApplicationUseCases) -> None:
    with pytest.raises(AIProfileNotFoundError):
        use_cases.update_ai_profile.execute(
            UpdateAIProfileRequest(
                profile_id="missing-profile-id", name="X", instructions="Y"
            )
        )
