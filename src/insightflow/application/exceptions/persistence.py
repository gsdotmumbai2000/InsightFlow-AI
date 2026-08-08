"""Application/infrastructure persistence exceptions."""

from __future__ import annotations


class PersistenceError(Exception):
    """Base persistence failure."""


class DatabaseUnavailableError(PersistenceError):
    """Raised when the database cannot be opened or used."""


class DuplicateEntityError(PersistenceError):
    """Raised when a uniqueness constraint is violated."""


class TransactionError(PersistenceError):
    """Raised when a transaction cannot be committed or rolled back."""


class DataMappingError(PersistenceError):
    """Raised when stored data cannot be mapped to a domain object."""
