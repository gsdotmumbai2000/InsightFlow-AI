"""Windows Credential Manager-backed SecretStore via keyring."""

from __future__ import annotations

import keyring
from keyring.errors import KeyringError

from insightflow.configuration.errors import (
    SecretStoreError,
    SecretStoreUnavailableError,
)

_SERVICE_NAME = "InsightFlowAI"


class WindowsKeyringSecretStore:
    """Stores secrets in the OS credential store (Windows Credential Manager)."""

    def save(self, name: str, value: str) -> None:
        key = _require_name(name)
        try:
            keyring.set_password(_SERVICE_NAME, key, value)
        except RecursionError as exc:
            raise SecretStoreUnavailableError(
                "Unable to save secret to the OS credential store."
            ) from exc
        except KeyringError as exc:
            raise SecretStoreUnavailableError(
                "Unable to save secret to the OS credential store."
            ) from exc

    def retrieve(self, name: str) -> str | None:
        key = _require_name(name)
        try:
            return keyring.get_password(_SERVICE_NAME, key)
        except RecursionError as exc:
            raise SecretStoreUnavailableError(
                "Unable to read secret from the OS credential store."
            ) from exc
        except KeyringError as exc:
            raise SecretStoreUnavailableError(
                "Unable to read secret from the OS credential store."
            ) from exc

    def delete(self, name: str) -> None:
        key = _require_name(name)
        try:
            keyring.delete_password(_SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            return
        except RecursionError as exc:
            raise SecretStoreUnavailableError(
                "Unable to delete secret from the OS credential store."
            ) from exc
        except KeyringError as exc:
            raise SecretStoreUnavailableError(
                "Unable to delete secret from the OS credential store."
            ) from exc

    def exists(self, name: str) -> bool:
        return self.retrieve(name) is not None


def _require_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise SecretStoreError("Secret name must not be empty.")
    return cleaned
