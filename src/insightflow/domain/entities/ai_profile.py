"""AIProfile entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from insightflow.domain.exceptions import DomainValidationError
from insightflow.domain.value_objects import AIProfileId
from insightflow.domain.value_objects._guards import (
    require_aware_utc,
    require_non_empty,
    utc_now,
)


@dataclass(slots=True)
class AIProfile:
    """Defines how events should be analyzed (provider-neutral)."""

    id: AIProfileId
    name: str
    description: str | None
    instructions: str
    version: int
    enabled: bool
    output_schema_version: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "AIProfile.name")
        self.instructions = require_non_empty(
            self.instructions, "AIProfile.instructions"
        )
        self.output_schema_version = require_non_empty(
            self.output_schema_version, "AIProfile.output_schema_version"
        )
        if self.description is not None:
            self.description = require_non_empty(
                self.description, "AIProfile.description"
            )
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise DomainValidationError("AIProfile.version must be an integer.")
        if self.version < 1:
            raise DomainValidationError(
                "AIProfile.version must be a positive integer (>= 1)."
            )
        self.created_at = require_aware_utc(self.created_at, "created_at")
        self.updated_at = require_aware_utc(self.updated_at, "updated_at")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        instructions: str,
        output_schema_version: str,
        description: str | None = None,
        version: int = 1,
        enabled: bool = True,
        profile_id: AIProfileId | None = None,
        created_at: datetime | None = None,
    ) -> AIProfile:
        timestamp = require_aware_utc(created_at or utc_now(), "created_at")
        return cls(
            id=profile_id or AIProfileId.generate(),
            name=name,
            description=description,
            instructions=instructions,
            version=version,
            enabled=enabled,
            output_schema_version=output_schema_version,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def enable(self, *, at: datetime | None = None) -> None:
        self.enabled = True
        self.updated_at = require_aware_utc(at or utc_now(), "at")

    def disable(self, *, at: datetime | None = None) -> None:
        self.enabled = False
        self.updated_at = require_aware_utc(at or utc_now(), "at")
