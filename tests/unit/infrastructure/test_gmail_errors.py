"""Gmail infrastructure error translation and adapter unit tests."""

from __future__ import annotations

import pytest

from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailAuthorizationError,
    GmailRateLimitError,
    GmailReauthenticationRequiredError,
    GmailUnavailableError,
)
from insightflow.infrastructure.gmail.errors import raise_translated_google_error
from insightflow.infrastructure.gmail.scopes import GMAIL_OAUTH_SCOPES, SCOPE_RATIONALE


def test_scopes_are_readonly_only() -> None:
    assert GMAIL_OAUTH_SCOPES == ("https://www.googleapis.com/auth/gmail.readonly",)
    assert "readonly" in SCOPE_RATIONALE


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (Exception("invalid_grant"), GmailReauthenticationRequiredError),
        (Exception("access_denied"), GmailAuthorizationError),
        (Exception("rate limit exceeded"), GmailRateLimitError),
        (Exception("service unavailable"), GmailUnavailableError),
        (Exception("oauth failed"), GmailAuthenticationError),
    ],
)
def test_google_error_translation(exc: Exception, expected: type[Exception]) -> None:
    with pytest.raises(expected):
        raise_translated_google_error(exc)
