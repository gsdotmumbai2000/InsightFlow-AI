"""Application entry point: ``python -m insightflow``."""

from __future__ import annotations

from insightflow.bootstrap.startup import main

if __name__ == "__main__":
    raise SystemExit(main())
