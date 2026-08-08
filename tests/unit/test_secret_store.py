"""SecretStore contract and safe in-memory implementation tests."""

from __future__ import annotations

import pytest

from insightflow.application.ports.secret_store import SecretStore
from insightflow.configuration.errors import SecretStoreUnavailableError
from insightflow.infrastructure.secrets.in_memory import InMemorySecretStore
from insightflow.infrastructure.secrets.unavailable import UnavailableSecretStore


def _assert_secret_store_contract(store: SecretStore) -> None:
    assert store.exists("token") is False
    assert store.retrieve("token") is None
    store.save("token", "value-1")
    assert store.exists("token") is True
    assert store.retrieve("token") == "value-1"
    store.save("token", "value-2")
    assert store.retrieve("token") == "value-2"
    store.delete("token")
    assert store.exists("token") is False
    assert store.retrieve("token") is None


def test_in_memory_secret_store_contract() -> None:
    store = InMemorySecretStore()
    assert isinstance(store, SecretStore)
    _assert_secret_store_contract(store)


def test_unavailable_secret_store_refuses_access() -> None:
    store = UnavailableSecretStore()
    with pytest.raises(SecretStoreUnavailableError):
        store.save("token", "value")
    with pytest.raises(SecretStoreUnavailableError):
        store.retrieve("token")
    with pytest.raises(SecretStoreUnavailableError):
        store.delete("token")
    with pytest.raises(SecretStoreUnavailableError):
        store.exists("token")
