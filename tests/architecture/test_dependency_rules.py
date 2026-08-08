"""Architecture tests enforcing dependency direction rules."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "insightflow"

FORBIDDEN_DOMAIN_PREFIXES = (
    "insightflow.infrastructure",
    "insightflow.presentation",
    "insightflow.bootstrap",
    "insightflow.configuration",
    "insightflow.application",
    "PySide6",
    "PySide2",
    "google",
    "googleapiclient",
    "google.cloud",
    "boto3",
    "botocore",
    "sqlalchemy",
    "sqlite3",
)

FORBIDDEN_APPLICATION_PREFIXES = (
    "insightflow.infrastructure",
    "insightflow.presentation",
    "PySide6",
    "PySide2",
    "google",
    "googleapiclient",
    "google.cloud",
    "boto3",
    "botocore",
    "openai",
    "sqlalchemy",
    "sqlite3",
)

FORBIDDEN_CONFIGURATION_PREFIXES = (
    "insightflow.infrastructure",
    "insightflow.presentation",
    "insightflow.bootstrap",
    "PySide6",
    "googleapiclient",
    "boto3",
)

FORBIDDEN_PRESENTATION_PREFIXES = (
    "insightflow.bootstrap",
    "sqlite3",
    "sqlalchemy",
    "insightflow.infrastructure",
    "google",
    "googleapiclient",
    "google.cloud",
    "boto3",
    "botocore",
    "openai",
)


def _iter_python_files(package_dir: Path) -> list[Path]:
    return sorted(path for path in package_dir.rglob("*.py") if path.is_file())


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _violations(package_dir: Path, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    for path in _iter_python_files(package_dir):
        for module in _imported_modules(path):
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            ):
                relative = path.relative_to(PACKAGE_ROOT)
                findings.append(f"{relative} imports forbidden module '{module}'")
    return findings


def test_domain_does_not_import_forbidden_dependencies() -> None:
    violations = _violations(PACKAGE_ROOT / "domain", FORBIDDEN_DOMAIN_PREFIXES)
    assert violations == [], "\n".join(violations)


def test_application_does_not_import_forbidden_dependencies() -> None:
    violations = _violations(
        PACKAGE_ROOT / "application",
        FORBIDDEN_APPLICATION_PREFIXES,
    )
    assert violations == [], "\n".join(violations)


def test_configuration_does_not_import_forbidden_dependencies() -> None:
    violations = _violations(
        PACKAGE_ROOT / "configuration",
        FORBIDDEN_CONFIGURATION_PREFIXES,
    )
    assert violations == [], "\n".join(violations)


def test_presentation_does_not_import_forbidden_dependencies() -> None:
    violations = _violations(
        PACKAGE_ROOT / "presentation",
        FORBIDDEN_PRESENTATION_PREFIXES,
    )
    assert violations == [], "\n".join(violations)


def test_presentation_may_import_application_and_configuration() -> None:
    """Smoke-check that presentation is allowed to depend on application."""
    modules: set[str] = set()
    for path in _iter_python_files(PACKAGE_ROOT / "presentation"):
        modules.update(_imported_modules(path))
    assert any(module.startswith("insightflow.application") for module in modules)
    assert any(module.startswith("PySide6") for module in modules)


def test_only_infrastructure_database_imports_sqlite3() -> None:
    findings: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        if "infrastructure" in path.parts and "database" in path.parts:
            continue
        for module in _imported_modules(path):
            if module == "sqlite3" or module.startswith("sqlite3."):
                findings.append(str(path.relative_to(PACKAGE_ROOT)))
    assert findings == [], (
        "sqlite3 imported outside infrastructure.database:\n" + "\n".join(findings)
    )


def test_infrastructure_gmail_may_import_google_sdk() -> None:
    modules: set[str] = set()
    for path in _iter_python_files(PACKAGE_ROOT / "infrastructure" / "gmail"):
        modules.update(_imported_modules(path))
    assert any(
        module == "google"
        or module.startswith("google.")
        or module.startswith("google_")
        or module.startswith("googleapiclient")
        for module in modules
    )


def test_non_gmail_layers_do_not_import_google_sdk() -> None:
    forbidden = (
        "google",
        "googleapiclient",
        "google.oauth2",
        "google_auth_oauthlib",
        "google.auth",
    )
    for layer in ("domain", "application", "presentation", "configuration"):
        violations = _violations(PACKAGE_ROOT / layer, forbidden)
        assert violations == [], "\n".join(violations)


def test_domain_only_imports_stdlib_or_domain() -> None:
    """Domain must remain pure: stdlib + insightflow.domain only."""
    allowed_third_party_prefixes = ("insightflow.domain",)
    stdlib_allowlist_prefixes = (
        "dataclasses",
        "datetime",
        "enum",
        "typing",
        "uuid",
        "collections",
        "abc",
        "functools",
        "itertools",
        "re",
        "math",
        "copy",
        "__future__",
    )
    findings: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT / "domain"):
        for module in _imported_modules(path):
            root = module.split(".", 1)[0]
            if module.startswith(allowed_third_party_prefixes):
                continue
            if root in stdlib_allowlist_prefixes or module in stdlib_allowlist_prefixes:
                continue
            if root == "insightflow":
                findings.append(
                    f"{path.relative_to(PACKAGE_ROOT)} imports non-domain "
                    f"insightflow module '{module}'"
                )
                continue
            if root not in {"builtins"}:
                findings.append(
                    f"{path.relative_to(PACKAGE_ROOT)} imports '{module}' "
                    "(domain must use stdlib + insightflow.domain only)"
                )
    assert findings == [], "\n".join(findings)
