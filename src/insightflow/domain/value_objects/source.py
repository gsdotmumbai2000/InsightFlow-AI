"""Provider-neutral source identity and topic source configuration."""

from __future__ import annotations

from dataclasses import dataclass

from insightflow.domain.enums import SourceType
from insightflow.domain.value_objects._guards import require_non_empty


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Provider-neutral reference to an external source occurrence."""

    source_type: SourceType
    source_id: str
    external_id: str
    thread_id: str | None = None
    account_id: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_id", require_non_empty(self.source_id, "source_id")
        )
        object.__setattr__(
            self, "external_id", require_non_empty(self.external_id, "external_id")
        )
        if self.thread_id is not None:
            object.__setattr__(
                self, "thread_id", require_non_empty(self.thread_id, "thread_id")
            )
        if self.account_id is not None:
            object.__setattr__(
                self, "account_id", require_non_empty(self.account_id, "account_id")
            )
        if self.url is not None:
            object.__setattr__(self, "url", require_non_empty(self.url, "url"))


@dataclass(frozen=True, slots=True)
class SourceConfiguration:
    """How a topic is bound to an external source identifier.

    Example: Gmail label ID is stored as ``source_identifier``, not as a
    Gmail SDK object.
    """

    source_type: SourceType
    source_id: str
    source_identifier: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_id", require_non_empty(self.source_id, "source_id")
        )
        object.__setattr__(
            self,
            "source_identifier",
            require_non_empty(self.source_identifier, "source_identifier"),
        )
