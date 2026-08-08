"""In-memory secret store for tests and ephemeral local development only."""

from __future__ import annotations

from insightflow.configuration.errors import SecretStoreError


class InMemorySecretStore:
    """Ephemeral secret store kept only in process memory.

    This implementation is intentionally unsuitable for production credentials.
    It exists for automated tests and explicit local development wiring.
    """

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def save(self, name: str, value: str) -> None:
        if not name.strip():
            raise SecretStoreError("Secret name must not be empty.")
        self._secrets[name] = value

    def retrieve(self, name: str) -> str | None:
        return self._secrets.get(name)

    def delete(self, name: str) -> None:
        self._secrets.pop(name, None)

    def exists(self, name: str) -> bool:
        return name in self._secrets
