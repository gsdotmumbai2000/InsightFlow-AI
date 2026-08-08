"""Bootstrap helpers for launching the presentation layer."""

from __future__ import annotations

from insightflow.bootstrap.container import AppContainer
from insightflow.presentation.models.context import PresentationContext


def presentation_context_from_container(
    container: AppContainer,
) -> PresentationContext:
    """Map composition-root container fields into a presentation context."""
    return PresentationContext(
        app_name=container.app_name,
        version=container.version,
        config=container.config,
        directories=container.directories,
        diagnostics=container.diagnostics,
        database_path=container.database_path,
        use_cases=container.use_cases,
    )
