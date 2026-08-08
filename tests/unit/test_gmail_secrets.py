"""SecretStore Gmail key and Windows backend tests."""

from __future__ import annotations

import pytest

from insightflow.application.ports.secret_store import SecretStore
from insightflow.bootstrap.dependencies import build_secret_store
from insightflow.configuration.env import MappingEnvironment
from insightflow.configuration.loader import load_config
from insightflow.configuration.models import SecretStoreBackend
from insightflow.infrastructure.secrets.in_memory import InMemorySecretStore
from insightflow.infrastructure.secrets.keys import GMAIL_OAUTH_TOKEN_KEY
from insightflow.infrastructure.secrets.windows_keyring import WindowsKeyringSecretStore


def test_gmail_token_stored_only_in_secret_store() -> None:
    store: SecretStore = InMemorySecretStore()
    store.save(GMAIL_OAUTH_TOKEN_KEY, '{"refresh_token":"secret-value"}')
    assert store.exists(GMAIL_OAUTH_TOKEN_KEY)
    assert store.retrieve(GMAIL_OAUTH_TOKEN_KEY) is not None
    store.delete(GMAIL_OAUTH_TOKEN_KEY)
    assert store.retrieve(GMAIL_OAUTH_TOKEN_KEY) is None


def test_production_cannot_use_memory_secret_store() -> None:
    with pytest.raises(Exception, match="not allowed in production"):
        load_config(
            environ=MappingEnvironment(
                {
                    "INSIGHTFLOW_ENV": "production",
                    "INSIGHTFLOW_SECRET_STORE": "memory",
                }
            )
        )


def test_windows_backend_selected_for_production_default() -> None:
    config = load_config(environ=MappingEnvironment({"INSIGHTFLOW_ENV": "production"}))
    assert config.security.secret_store_backend is SecretStoreBackend.WINDOWS
    store = build_secret_store(config)
    assert isinstance(store, WindowsKeyringSecretStore)


def test_windows_keyring_store_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    backend: dict[str, str] = {}

    def fake_set(service: str, username: str, password: str) -> None:
        backend[f"{service}:{username}"] = password

    def fake_get(service: str, username: str) -> str | None:
        return backend.get(f"{service}:{username}")

    def fake_delete(service: str, username: str) -> None:
        backend.pop(f"{service}:{username}", None)

    monkeypatch.setattr(
        "insightflow.infrastructure.secrets.windows_keyring.keyring.set_password",
        fake_set,
    )
    monkeypatch.setattr(
        "insightflow.infrastructure.secrets.windows_keyring.keyring.get_password",
        fake_get,
    )
    monkeypatch.setattr(
        "insightflow.infrastructure.secrets.windows_keyring.keyring.delete_password",
        fake_delete,
    )

    store = WindowsKeyringSecretStore()
    store.save(GMAIL_OAUTH_TOKEN_KEY, "token-json")
    assert store.retrieve(GMAIL_OAUTH_TOKEN_KEY) == "token-json"
    assert store.exists(GMAIL_OAUTH_TOKEN_KEY)
    store.delete(GMAIL_OAUTH_TOKEN_KEY)
    assert store.retrieve(GMAIL_OAUTH_TOKEN_KEY) is None
