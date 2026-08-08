"""Configuration-layer errors."""

from __future__ import annotations


class ConfigurationError(Exception):
    """Raised when application configuration is missing or invalid."""


class SecretStoreError(Exception):
    """Base error for secret-store operations."""


class SecretStoreUnavailableError(SecretStoreError):
    """Raised when no secure secret store is available for the current environment."""
