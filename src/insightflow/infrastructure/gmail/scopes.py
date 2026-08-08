"""Gmail OAuth scopes documentation and constants."""

from __future__ import annotations

# Read-only Gmail access: list labels now; read messages in later phases.
# Does not include send, modify, or delete permissions.
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

GMAIL_OAUTH_SCOPES: tuple[str, ...] = (GMAIL_READONLY_SCOPE,)

SCOPE_RATIONALE = (
    "gmail.readonly is required to discover labels and, in later phases, "
    "read message content for intelligence monitoring. "
    "Send/modify scopes are intentionally omitted."
)
