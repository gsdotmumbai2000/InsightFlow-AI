"""Application shutdown orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from insightflow.infrastructure.logging.setup import get_logger

if TYPE_CHECKING:
    from insightflow.bootstrap.startup import Application

logger = get_logger("bootstrap.shutdown")


def shutdown(app: Application) -> None:
    """Release resources held by a running application."""
    logger.info(
        "Shutting down %s v%s",
        app.container.app_name,
        app.container.version,
    )
