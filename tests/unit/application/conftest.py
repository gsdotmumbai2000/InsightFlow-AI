"""Shared fixtures for application use-case unit tests."""

from __future__ import annotations

import pytest
from tests.fakes.gmail import FakeGmailAdapter
from tests.unit.application.fakes import InMemoryStore

from insightflow.application.use_cases import ApplicationUseCases, build_use_cases


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def gmail() -> FakeGmailAdapter:
    return FakeGmailAdapter()


@pytest.fixture
def use_cases(store: InMemoryStore, gmail: FakeGmailAdapter) -> ApplicationUseCases:
    return build_use_cases(
        store.unit_of_work_factory,
        gmail_authenticator=gmail,
        gmail_labels=gmail,
    )
