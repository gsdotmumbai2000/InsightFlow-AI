"""Confidence and content-hash value objects."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.domain.exceptions import DomainValidationError
from insightflow.domain.value_objects._guards import require_non_empty


@dataclass(frozen=True, slots=True)
class Confidence:
    """Confidence score in the inclusive range ``[0.0, 1.0]``."""

    value: float

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int | float):
            raise DomainValidationError("Confidence must be a number.")
        numeric = float(self.value)
        if numeric < 0.0 or numeric > 1.0:
            raise DomainValidationError(
                f"Confidence must be between 0 and 1 inclusive; got {numeric}."
            )
        object.__setattr__(self, "value", numeric)


@dataclass(frozen=True, slots=True)
class ContentHash:
    """Opaque content hash (typically SHA-256 hex) for duplicate detection."""

    value: str

    def __post_init__(self) -> None:
        cleaned = require_non_empty(self.value, "ContentHash")
        object.__setattr__(self, "value", cleaned.lower())


@dataclass(frozen=True, slots=True)
class StorageReference:
    """Provider-neutral reference to stored binary content.

    The domain does not interpret filesystem paths or cloud URIs.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", require_non_empty(self.value, "StorageReference")
        )
