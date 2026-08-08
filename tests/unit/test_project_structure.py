"""Tests verifying the documented project package layout."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "src" / "insightflow"

REQUIRED_LAYERS = (
    "domain",
    "application",
    "infrastructure",
    "presentation",
    "configuration",
    "shared",
    "bootstrap",
)

REQUIRED_DOMAIN_PACKAGES = (
    "entities",
    "value_objects",
    "enums",
    "events",
    "policies",
    "services",
    "repositories",
    "exceptions",
)

REQUIRED_APPLICATION_PACKAGES = (
    "commands",
    "queries",
    "services",
    "dto",
    "ports",
    "workflows",
    "exceptions",
)

REQUIRED_TEST_ROOTS = (
    "unit",
    "integration",
    "architecture",
    "e2e",
)


def test_required_layers_exist() -> None:
    for layer in REQUIRED_LAYERS:
        path = PACKAGE_ROOT / layer
        assert path.is_dir(), f"Missing layer package: {layer}"
        assert (path / "__init__.py").is_file(), f"Missing __init__.py for {layer}"


def test_domain_subpackages_exist() -> None:
    for name in REQUIRED_DOMAIN_PACKAGES:
        path = PACKAGE_ROOT / "domain" / name
        assert path.is_dir(), f"Missing domain package: {name}"
        assert (path / "__init__.py").is_file()


def test_application_subpackages_exist() -> None:
    for name in REQUIRED_APPLICATION_PACKAGES:
        path = PACKAGE_ROOT / "application" / name
        assert path.is_dir(), f"Missing application package: {name}"
        assert (path / "__init__.py").is_file()


def test_bootstrap_modules_exist() -> None:
    bootstrap = PACKAGE_ROOT / "bootstrap"
    for module in ("container.py", "dependencies.py", "startup.py", "shutdown.py"):
        assert (bootstrap / module).is_file(), f"Missing bootstrap module: {module}"


def test_entry_point_module_exists() -> None:
    assert (PACKAGE_ROOT / "__main__.py").is_file()


def test_test_layout_exists() -> None:
    tests_root = ROOT / "tests"
    for name in REQUIRED_TEST_ROOTS:
        assert (tests_root / name).is_dir(), f"Missing tests/{name}"
