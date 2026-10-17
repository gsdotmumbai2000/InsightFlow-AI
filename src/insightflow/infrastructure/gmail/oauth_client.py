"""Shared Google OAuth client-config loading (Gmail + Pub/Sub, Phase 10).

Both the Gmail adapter and the desktop Pub/Sub subscriber authorize
against the *same* Google Cloud OAuth client — only the requested scopes
and the resulting stored token differ (see
``infrastructure/pubsub/oauth.py``). Centralizing client-config loading
here avoids duplicating credential-management logic per the project's
"do not create duplicate credential management" rule.
"""

from __future__ import annotations

import json
from typing import Any, cast

from insightflow.application.exceptions.gmail import GmailConfigurationError
from insightflow.application.ports.secret_store import SecretStore
from insightflow.configuration.models import GmailSettings
from insightflow.infrastructure.secrets.keys import GMAIL_OAUTH_CLIENT_SECRET_KEY


def load_google_oauth_client_config(
    settings: GmailSettings, secret_store: SecretStore
) -> dict[str, Any]:
    """Load the installed-app OAuth client config from file or settings."""
    if settings.client_secrets_file is not None:
        path = settings.client_secrets_file
        if not path.is_file():
            raise GmailConfigurationError(
                f"Gmail client secrets file was not found: {path}"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GmailConfigurationError(
                "Unable to read Gmail client secrets file."
            ) from exc
        if not isinstance(payload, dict):
            raise GmailConfigurationError(
                "Gmail client secrets file must contain a JSON object."
            )
        if "installed" not in payload and "web" not in payload:
            raise GmailConfigurationError(
                "Gmail client secrets file must contain an installed or web client."
            )
        return cast(dict[str, Any], payload)

    client_id = settings.client_id
    client_secret = settings.client_secret
    if not client_secret:
        client_secret = secret_store.retrieve(GMAIL_OAUTH_CLIENT_SECRET_KEY)
    if not client_id or not client_secret:
        raise GmailConfigurationError(
            "Gmail OAuth is not configured. Set INSIGHTFLOW_GMAIL_CLIENT_ID and "
            "INSIGHTFLOW_GMAIL_CLIENT_SECRET, or "
            "INSIGHTFLOW_GMAIL_CLIENT_SECRETS_FILE."
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
