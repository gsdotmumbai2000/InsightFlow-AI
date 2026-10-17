"""Pub/Sub OAuth credential provider (Phase 10).

Deliberately separate from Gmail OAuth: this requests the additional
``pubsub`` scope through its own consent step and its own stored token
(SecretStore key), so a user who never enables real-time monitoring never
grants Pub/Sub access. Reuses the same OAuth *client* configuration as
Gmail (``load_google_oauth_client_config``) — not duplicated credential
management, just a separate authorization and a separate stored token.
"""

from __future__ import annotations

import json
import logging
from typing import cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from insightflow.application.exceptions.pubsub import (
    PubSubAuthenticationError,
    PubSubConfigurationError,
)
from insightflow.application.ports.secret_store import SecretStore
from insightflow.configuration.models import GmailSettings
from insightflow.infrastructure.gmail.oauth_client import (
    load_google_oauth_client_config,
)
from insightflow.infrastructure.secrets.keys import GMAIL_PUBSUB_OAUTH_TOKEN_KEY

logger = logging.getLogger("insightflow.infrastructure.pubsub")

PUBSUB_OAUTH_SCOPE = "https://www.googleapis.com/auth/pubsub"
PUBSUB_OAUTH_SCOPES: tuple[str, ...] = (PUBSUB_OAUTH_SCOPE,)


class GooglePubSubAuthenticator:
    """Implements ``PubSubAuthenticator`` (connect/disconnect/is_connected)."""

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

    def connect(self) -> None:
        client_config = load_google_oauth_client_config(self._settings, self._secrets)
        try:
            flow = InstalledAppFlow.from_client_config(
                client_config, scopes=list(PUBSUB_OAUTH_SCOPES)
            )
            credentials = flow.run_local_server(
                port=self._oauth_port,
                open_browser=True,
                authorization_prompt_message=(
                    "Opening browser for Pub/Sub authorization…"
                ),
                success_message=(
                    "Pub/Sub authorization complete. You may close this browser "
                    "window and return to InsightFlow AI."
                ),
            )
        except Exception as exc:
            if "access_denied" in str(exc).lower():
                raise PubSubAuthenticationError(
                    "Pub/Sub authorization was denied or cancelled."
                ) from exc
            raise PubSubAuthenticationError("Pub/Sub authorization failed.") from exc

        token_json = cast(str, credentials.to_json())
        self._secrets.save(GMAIL_PUBSUB_OAUTH_TOKEN_KEY, token_json)
        logger.info("Pub/Sub subscriber authorized.")

    def disconnect(self) -> None:
        self._secrets.delete(GMAIL_PUBSUB_OAUTH_TOKEN_KEY)
        logger.info("Pub/Sub authorization removed.")

    def is_connected(self) -> bool:
        return self._secrets.exists(GMAIL_PUBSUB_OAUTH_TOKEN_KEY)

    def credentials(self) -> Credentials:
        """Return valid Pub/Sub credentials, refreshing if necessary."""
        raw = self._secrets.retrieve(GMAIL_PUBSUB_OAUTH_TOKEN_KEY)
        if not raw:
            raise PubSubConfigurationError(
                "Pub/Sub is not authorized. Authorize Pub/Sub access first."
            )
        try:
            loaded = Credentials.from_authorized_user_info(  # type: ignore[no-untyped-call]
                json.loads(raw), scopes=list(PUBSUB_OAUTH_SCOPES)
            )
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise PubSubAuthenticationError(
                "Stored Pub/Sub credentials are invalid. Authorize again."
            ) from exc
        credentials = cast(Credentials, loaded)
        if not credentials.valid:
            if not credentials.refresh_token:
                raise PubSubAuthenticationError(
                    "Pub/Sub credentials require re-authorization."
                )
            try:
                credentials.refresh(Request())  # type: ignore[no-untyped-call]
                self._secrets.save(
                    GMAIL_PUBSUB_OAUTH_TOKEN_KEY,
                    cast(str, credentials.to_json()),  # type: ignore[no-untyped-call]
                )
            except Exception as exc:
                raise PubSubAuthenticationError(
                    "Pub/Sub token refresh failed. Authorize again."
                ) from exc
        return credentials
