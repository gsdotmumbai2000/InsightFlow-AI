"""Centralized environment variable access for configuration loading."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class EnvironmentSource(Protocol):
    """Abstraction over process environment lookups."""

    def get(self, key: str) -> str | None:
        """Return the raw value for ``key``, or ``None`` when unset."""


class OsEnvironment:
    """Reads values from the process environment."""

    def get(self, key: str) -> str | None:
        return os.environ.get(key)


class MappingEnvironment:
    """Environment backed by an in-memory mapping (tests and composition)."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)

    def get(self, key: str) -> str | None:
        return self._values.get(key)


class OverlayEnvironment:
    """Lookup order: overlay first, then base."""

    def __init__(self, *, base: EnvironmentSource, overlay: EnvironmentSource) -> None:
        self._base = base
        self._overlay = overlay

    def get(self, key: str) -> str | None:
        value = self._overlay.get(key)
        if value is not None:
            return value
        return self._base.get(key)


def load_dotenv_file(path: Path) -> dict[str, str]:
    """Parse a simple ``KEY=VALUE`` dotenv file.

    Lines starting with ``#`` and blank lines are ignored.
    Values may be optionally wrapped in single or double quotes.
    """
    if not path.is_file():
        return {}

    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    return result
