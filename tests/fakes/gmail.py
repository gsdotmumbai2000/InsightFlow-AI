"""In-memory fake Gmail ports for unit tests (no network)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
)
from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailConfigurationError,
    GmailConnectionError,
    GmailReauthenticationRequiredError,
)


@dataclass
class FakeGmailAdapter:
    """Test double implementing authenticator + label provider."""

    configured: bool = True
    fail_connect: bool = False
    require_reauth: bool = False
    account: GmailAccountDto | None = None
    labels: list[GmailLabelDto] = field(default_factory=list)
    connected: bool = False
    token_value: str | None = None

    def connect(self) -> GmailAccountDto:
        if not self.configured:
            raise GmailConfigurationError("Gmail OAuth is not configured.")
        if self.fail_connect:
            raise GmailAuthenticationError("Gmail authentication failed.")
        self.connected = True
        self.require_reauth = False
        self.token_value = "fake-refresh-token-not-for-dto"
        if self.account is None:
            self.account = GmailAccountDto(
                account_id="user@example.com",
                email="user@example.com",
                display_name="Example User",
            )
        return self.account

    def disconnect(self) -> None:
        self.connected = False
        self.token_value = None
        self.require_reauth = False

    def get_connection_status(self) -> GmailConnectionStatusDto:
        if self.require_reauth:
            return GmailConnectionStatusDto(
                status="REAUTHENTICATION_REQUIRED",
                message="Gmail requires re-authentication.",
            )
        if not self.connected or self.account is None:
            return GmailConnectionStatusDto(
                status="NOT_CONNECTED",
                message="Gmail is not connected.",
            )
        return GmailConnectionStatusDto(
            status="CONNECTED",
            account=self.account,
            last_verified_at=datetime.now(UTC),
            message="Gmail is connected.",
        )

    def get_account(self) -> GmailAccountDto | None:
        if not self.connected:
            return None
        return self.account

    def list_labels(self) -> list[GmailLabelDto]:
        if self.require_reauth:
            raise GmailReauthenticationRequiredError(
                "Gmail requires re-authentication."
            )
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        return list(self.labels)
