"""Application port for secure secret storage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretStore(Protocol):
    """Secure secret storage contract used by the application layer."""

    def save(self, name: str, value: str) -> None:
        """Persist a secret value under ``name``."""

    def retrieve(self, name: str) -> str | None:
        """Return the secret value for ``name``, or ``None`` if absent."""

    def delete(self, name: str) -> None:
        """Delete the secret named ``name`` if it exists."""

    def exists(self, name: str) -> bool:
        """Return whether a secret named ``name`` exists."""
