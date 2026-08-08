"""Unit tests for package importability."""

from __future__ import annotations


def test_insightflow_package_imports() -> None:
    import insightflow

    assert insightflow.__version__ == "0.1.0"


def test_core_layers_import() -> None:
    import insightflow.application
    import insightflow.bootstrap
    import insightflow.configuration
    import insightflow.domain
    import insightflow.infrastructure
    import insightflow.presentation
    import insightflow.shared
    from insightflow.application.ports import SecretStore
    from insightflow.shared import create_correlation_id

    assert insightflow.domain.__name__ == "insightflow.domain"
    assert insightflow.application.__name__ == "insightflow.application"
    assert insightflow.infrastructure.__name__ == "insightflow.infrastructure"
    assert insightflow.presentation.__name__ == "insightflow.presentation"
    assert insightflow.configuration.__name__ == "insightflow.configuration"
    assert insightflow.shared.__name__ == "insightflow.shared"
    assert insightflow.bootstrap.__name__ == "insightflow.bootstrap"
    assert SecretStore is not None
    assert create_correlation_id()
