"""In-memory fake Gmail ports for unit tests (no network)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from insightflow.application.dto.email import (
    EmailMessageDto,
    GmailMessageListPageDto,
    GmailMessageRefDto,
    ListGmailMessagesRequest,
)
from insightflow.application.dto.gmail import (
    GmailAccountDto,
    GmailConnectionStatusDto,
    GmailLabelDto,
)
from insightflow.application.dto.monitoring import (
    GmailHistoryPageDto,
    GmailWatchResultDto,
)
from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailConfigurationError,
    GmailConnectionError,
    GmailHistoryUnavailableError,
    GmailMessageNotFoundError,
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

    # -- GmailMessageProvider (Phase 8) --------------------------------
    message_ids_by_label: dict[str, list[str]] = field(default_factory=dict)
    messages_by_id: dict[str, EmailMessageDto] = field(default_factory=dict)
    fail_message_ids: set[str] = field(default_factory=set)
    list_page_size: int | None = None
    list_calls: int = field(default=0, compare=False)
    get_calls: list[str] = field(default_factory=list, compare=False)

    # -- GmailWatchProvider / GmailHistoryProvider (Phase 10) ----------
    watch_history_id: str = "1000"
    watch_expiration: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(days=7)
    )
    watch_calls: list[tuple[tuple[str, ...], str]] = field(
        default_factory=list, compare=False
    )
    stop_watch_calls: int = field(default=0, compare=False)
    unavailable_history_ids: set[str] = field(default_factory=set)
    history_pages_by_start_id: dict[str, list[GmailHistoryPageDto]] = field(
        default_factory=dict
    )
    history_calls: list[str] = field(default_factory=list, compare=False)

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

    def list_message_ids(
        self, request: ListGmailMessagesRequest
    ) -> GmailMessageListPageDto:
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        self.list_calls += 1
        all_ids = self.message_ids_by_label.get(request.label_id, [])
        start = int(request.page_token) if request.page_token else 0
        page_size = request.max_results
        if self.list_page_size is not None:
            page_size = min(page_size, self.list_page_size)
        end = start + max(page_size, 1)
        page_ids = all_ids[start:end]
        next_token = str(end) if end < len(all_ids) else None
        refs = [
            GmailMessageRefDto(message_id=mid, thread_id=f"thread-{mid}")
            for mid in page_ids
        ]
        return GmailMessageListPageDto(
            messages=tuple(refs),
            next_page_token=next_token,
            result_size_estimate=len(all_ids),
        )

    def get_message(self, message_id: str) -> EmailMessageDto:
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        self.get_calls.append(message_id)
        if message_id in self.fail_message_ids:
            raise GmailMessageNotFoundError(
                f"Gmail message {message_id} could not be found."
            )
        message = self.messages_by_id.get(message_id)
        if message is None:
            raise GmailMessageNotFoundError(
                f"Gmail message {message_id} could not be found."
            )
        return message

    def start_watch(
        self, *, label_ids: tuple[str, ...], pubsub_topic: str
    ) -> GmailWatchResultDto:
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        self.watch_calls.append((tuple(label_ids), pubsub_topic))
        return GmailWatchResultDto(
            history_id=self.watch_history_id, expiration=self.watch_expiration
        )

    def stop_watch(self) -> None:
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        self.stop_watch_calls += 1

    def list_history(
        self,
        *,
        start_history_id: str,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> GmailHistoryPageDto:
        if not self.connected:
            raise GmailConnectionError("Gmail is not connected.")
        self.history_calls.append(start_history_id)
        if start_history_id in self.unavailable_history_ids:
            raise GmailHistoryUnavailableError(
                f"History position unavailable: {start_history_id}"
            )
        pages = self.history_pages_by_start_id.get(start_history_id, [])
        index = int(page_token) if page_token else 0
        if index >= len(pages):
            return GmailHistoryPageDto(
                records=(), next_page_token=None, history_id=self.watch_history_id
            )
        return pages[index]
