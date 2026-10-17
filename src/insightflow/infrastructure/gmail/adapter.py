"""Concrete Gmail OAuth + label provider using official Google libraries."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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
from insightflow.application.exceptions.gmail import (
    GmailAuthenticationError,
    GmailConnectionError,
    GmailMessageParsingError,
    GmailReauthenticationRequiredError,
)
from insightflow.application.ports.secret_store import SecretStore
from insightflow.configuration.models import GmailSettings
from insightflow.infrastructure.gmail.errors import raise_translated_google_error
from insightflow.infrastructure.gmail.message_mapper import map_gmail_message_to_dto
from insightflow.infrastructure.gmail.mime import DEFAULT_MAX_BODY_BYTES
from insightflow.infrastructure.gmail.oauth_client import (
    load_google_oauth_client_config,
)
from insightflow.infrastructure.gmail.scopes import GMAIL_OAUTH_SCOPES
from insightflow.infrastructure.secrets.keys import (
    GMAIL_ACCOUNT_PROFILE_KEY,
    GMAIL_OAUTH_TOKEN_KEY,
)

logger = logging.getLogger("insightflow.infrastructure.gmail")

_STATUS_NOT_CONNECTED = "NOT_CONNECTED"
_STATUS_CONNECTED = "CONNECTED"
_STATUS_REAUTH = "REAUTHENTICATION_REQUIRED"
_STATUS_FAILED = "CONNECTION_FAILED"

# Google documents a maximum of 500 results per users.messages.list call.
GMAIL_LIST_MAX_RESULTS = 500


@dataclass(frozen=True, slots=True)
class _AccountProfile:
    account_id: str
    email: str
    display_name: str | None
    last_verified_at: str | None


class GoogleGmailAdapter:
    """Implements GmailAuthenticator + GmailLabelProvider against Google APIs."""

    def __init__(
        self,
        *,
        settings: GmailSettings,
        secret_store: SecretStore,
        oauth_port: int = 0,
    ) -> None:
        self._settings = settings
        self._secrets = secret_store
        self._oauth_port = oauth_port

    def connect(self) -> GmailAccountDto:
        client_config = self._load_client_config()
        try:
            flow = InstalledAppFlow.from_client_config(
                client_config, scopes=list(GMAIL_OAUTH_SCOPES)
            )
            credentials = flow.run_local_server(
                port=self._oauth_port,
                open_browser=True,
                authorization_prompt_message=(
                    "Opening browser for Google authorization…"
                ),
                success_message=(
                    "Authorization complete. You may close this browser window "
                    "and return to InsightFlow AI."
                ),
            )
        except Exception as exc:
            if "access_denied" in str(exc).lower():
                raise GmailAuthenticationError(
                    "Gmail authorization was denied or cancelled."
                ) from exc
            raise_translated_google_error(exc)

        self._save_credentials(credentials)
        account = self._fetch_and_store_profile(credentials)
        logger.info(
            "Gmail connected for account_id=%s email=%s",
            account.account_id,
            account.email,
        )
        return account

    def disconnect(self) -> None:
        self._secrets.delete(GMAIL_OAUTH_TOKEN_KEY)
        self._secrets.delete(GMAIL_ACCOUNT_PROFILE_KEY)
        logger.info("Gmail disconnected; stored credentials removed.")

    def get_connection_status(self) -> GmailConnectionStatusDto:
        if not self._secrets.exists(GMAIL_OAUTH_TOKEN_KEY):
            return GmailConnectionStatusDto(
                status=_STATUS_NOT_CONNECTED,
                message="Gmail is not connected.",
            )
        try:
            credentials = self._load_credentials()
            if credentials is None:
                return GmailConnectionStatusDto(
                    status=_STATUS_NOT_CONNECTED,
                    message="Gmail is not connected.",
                )
            if not credentials.valid:
                if credentials.refresh_token:
                    try:
                        credentials.refresh(Request())  # type: ignore[no-untyped-call]
                        self._save_credentials(credentials)
                    except Exception as exc:
                        logger.warning("Gmail token refresh failed.")
                        raise_translated_google_error(exc)
                else:
                    return GmailConnectionStatusDto(
                        status=_STATUS_REAUTH,
                        message="Gmail requires re-authentication.",
                    )
            account = self.get_account()
            verified_at = None
            profile = self._load_profile()
            if profile and profile.last_verified_at:
                verified_at = datetime.fromisoformat(profile.last_verified_at)
            return GmailConnectionStatusDto(
                status=_STATUS_CONNECTED,
                account=account,
                last_verified_at=verified_at,
                message="Gmail is connected.",
            )
        except GmailReauthenticationRequiredError as exc:
            return GmailConnectionStatusDto(
                status=_STATUS_REAUTH,
                message=str(exc),
            )
        except Exception as exc:
            # Avoid logging when the stack is already exhausted (e.g. UI re-entry).
            if not isinstance(exc, RecursionError):
                logger.warning(
                    "Gmail connection status check failed: %s", type(exc).__name__
                )
            return GmailConnectionStatusDto(
                status=_STATUS_FAILED,
                message="Gmail connection check failed.",
            )

    def get_account(self) -> GmailAccountDto | None:
        profile = self._load_profile()
        if profile is None:
            return None
        return GmailAccountDto(
            account_id=profile.account_id,
            email=profile.email,
            display_name=profile.display_name,
        )

    def list_labels(self) -> list[GmailLabelDto]:
        credentials = self._require_valid_credentials()
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            response = service.users().labels().list(userId="me").execute()
        except Exception as exc:
            raise_translated_google_error(exc)

        labels = response.get("labels", []) if isinstance(response, dict) else []
        result: list[GmailLabelDto] = []
        for item in labels:
            if not isinstance(item, dict):
                continue
            label_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            if not label_id or not name:
                continue
            result.append(
                GmailLabelDto(
                    label_id=label_id,
                    name=name,
                    label_type=str(item.get("type") or "user"),
                    message_list_visibility=item.get("messageListVisibility"),
                    label_list_visibility=item.get("labelListVisibility"),
                )
            )
        result.sort(key=lambda label: label.name.lower())
        logger.info("Listed %s Gmail labels", len(result))
        return result

    def list_message_ids(
        self, request: ListGmailMessagesRequest
    ) -> GmailMessageListPageDto:
        """List message references for one label (bounded, paginated)."""
        credentials = self._require_valid_credentials()
        capped_max_results = max(1, min(request.max_results, GMAIL_LIST_MAX_RESULTS))
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            response = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[request.label_id],
                    maxResults=capped_max_results,
                    pageToken=request.page_token,
                )
                .execute()
            )
        except Exception as exc:
            raise_translated_google_error(exc)

        raw_messages = (
            response.get("messages", []) if isinstance(response, dict) else []
        )
        refs = tuple(
            GmailMessageRefDto(
                message_id=str(item["id"]), thread_id=item.get("threadId")
            )
            for item in raw_messages
            if isinstance(item, dict) and item.get("id")
        )
        return GmailMessageListPageDto(
            messages=refs,
            next_page_token=response.get("nextPageToken"),
            result_size_estimate=response.get("resultSizeEstimate"),
        )

    def get_message(self, message_id: str) -> EmailMessageDto:
        """Retrieve and normalize a single Gmail message (format=FULL)."""
        credentials = self._require_valid_credentials()
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            raw = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as exc:
            raise_translated_google_error(exc)

        try:
            return map_gmail_message_to_dto(raw, max_body_bytes=DEFAULT_MAX_BODY_BYTES)
        except Exception as exc:
            logger.warning(
                "Failed to normalize Gmail message id=%s error=%s",
                message_id,
                type(exc).__name__,
            )
            raise GmailMessageParsingError(
                f"Gmail message {message_id} could not be parsed."
            ) from exc

    def _require_valid_credentials(self) -> Credentials:
        credentials = self._load_credentials()
        if credentials is None:
            raise GmailConnectionError("Gmail is not connected.")
        if not credentials.valid:
            if not credentials.refresh_token:
                raise GmailReauthenticationRequiredError(
                    "Gmail requires re-authentication."
                )
            try:
                credentials.refresh(Request())  # type: ignore[no-untyped-call]
                self._save_credentials(credentials)
            except Exception as exc:
                raise_translated_google_error(exc)
        return credentials

    def _load_client_config(self) -> dict[str, Any]:
        return load_google_oauth_client_config(self._settings, self._secrets)

    def gmail_credentials(self) -> Credentials:
        """Public accessor for a valid credentials object (Phase 10).

        Lets ``GoogleGmailMonitoringAdapter`` (Watch/History) reuse this
        adapter's Gmail credential management without duplicating it.
        """
        return self._require_valid_credentials()

    def _save_credentials(self, credentials: Credentials) -> None:
        # Persist token JSON only — never log this payload.
        token_json = cast(str, credentials.to_json())  # type: ignore[no-untyped-call]
        self._secrets.save(GMAIL_OAUTH_TOKEN_KEY, token_json)

    def _load_credentials(self) -> Credentials | None:
        raw = self._secrets.retrieve(GMAIL_OAUTH_TOKEN_KEY)
        if not raw:
            return None
        try:
            loaded = Credentials.from_authorized_user_info(  # type: ignore[no-untyped-call]
                json.loads(raw), scopes=list(GMAIL_OAUTH_SCOPES)
            )
            return cast(Credentials, loaded)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Stored Gmail credentials are unreadable.")
            raise GmailReauthenticationRequiredError(
                "Stored Gmail credentials are invalid. Please connect Gmail again."
            ) from exc

    def _fetch_and_store_profile(self, credentials: Credentials) -> GmailAccountDto:
        try:
            service = build(
                "gmail", "v1", credentials=credentials, cache_discovery=False
            )
            profile = service.users().getProfile(userId="me").execute()
        except Exception as exc:
            raise_translated_google_error(exc)

        email = str(profile.get("emailAddress") or "").strip()
        account_id = str(profile.get("emailAddress") or "").strip()
        if not email or not account_id:
            raise GmailConnectionError(
                "Gmail profile did not include an email address."
            )
        now = datetime.now(UTC).isoformat()
        payload = {
            "account_id": account_id,
            "email": email,
            "display_name": None,
            "last_verified_at": now,
        }
        self._secrets.save(GMAIL_ACCOUNT_PROFILE_KEY, json.dumps(payload))
        return GmailAccountDto(
            account_id=account_id,
            email=email,
            display_name=None,
        )

    def _load_profile(self) -> _AccountProfile | None:
        raw = self._secrets.retrieve(GMAIL_ACCOUNT_PROFILE_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return _AccountProfile(
                account_id=str(data["account_id"]),
                email=str(data["email"]),
                display_name=data.get("display_name"),
                last_verified_at=data.get("last_verified_at"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return None


def resolve_client_secrets_path(raw: str | None) -> Path | None:
    if raw is None or not raw.strip():
        return None
    return Path(raw.strip()).expanduser()
