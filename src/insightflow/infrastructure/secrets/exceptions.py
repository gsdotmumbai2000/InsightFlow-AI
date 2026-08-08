"""Secret-store infrastructure exceptions."""

from __future__ import annotations

from insightflow.configuration.errors import (
    SecretStoreError,
    SecretStoreUnavailableError,
)

__all__ = ["SecretStoreError", "SecretStoreUnavailableError"]
