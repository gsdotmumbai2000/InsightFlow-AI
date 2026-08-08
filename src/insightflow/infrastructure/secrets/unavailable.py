"""Unavailable secret store used until a secure OS backend is wired."""

from __future__ import annotations

from insightflow.configuration.errors import SecretStoreUnavailableError


class UnavailableSecretStore:
    """Secret store that refuses all access with an explicit error.

    Production must not silently fall back to insecure storage. Until a
    Windows credential-store adapter is implemented, this backend makes the
    absence of a secure store obvious.
    """

    def save(self, name: str, value: str) -> None:
        raise SecretStoreUnavailableError(
            "Secure secret storage is not configured for this environment. "
            f"Cannot save secret {name!r}."
        )

    def retrieve(self, name: str) -> str | None:
        raise SecretStoreUnavailableError(
            "Secure secret storage is not configured for this environment. "
            f"Cannot retrieve secret {name!r}."
        )

    def delete(self, name: str) -> None:
        raise SecretStoreUnavailableError(
            "Secure secret storage is not configured for this environment. "
            f"Cannot delete secret {name!r}."
        )

    def exists(self, name: str) -> bool:
        raise SecretStoreUnavailableError(
            "Secure secret storage is not configured for this environment. "
            f"Cannot check secret {name!r}."
        )
