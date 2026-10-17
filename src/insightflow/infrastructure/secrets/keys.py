"""Stable SecretStore key names for Gmail/Pub/Sub OAuth credentials."""

from __future__ import annotations

# Authorized-user token JSON (access + refresh). Never log or expose in DTOs.
GMAIL_OAUTH_TOKEN_KEY = "insightflow.gmail.oauth.token"

# Optional client secret when not using a client-secrets JSON file.
GMAIL_OAUTH_CLIENT_SECRET_KEY = "insightflow.gmail.oauth.client_secret"

# Non-token account profile JSON: account_id, email, display_name, last_verified_at.
GMAIL_ACCOUNT_PROFILE_KEY = "insightflow.gmail.account.profile"

# Separate authorized-user token JSON for the desktop Pub/Sub subscriber
# (``pubsub`` scope only). Deliberately distinct from GMAIL_OAUTH_TOKEN_KEY —
# a user who never enables real-time monitoring never grants this scope.
GMAIL_PUBSUB_OAUTH_TOKEN_KEY = "insightflow.gmail.pubsub.oauth.token"
