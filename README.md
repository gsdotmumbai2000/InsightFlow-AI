# InsightFlow AI

Desktop-first AI-powered intelligence and content automation platform.

## Requirements

- Python **3.13+**
- Windows (initial target platform)

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` for local development settings.

## Commands

```powershell
# Run the application (Phase 1: minimal startup)
python -m insightflow

# Tests
pytest

# Lint / format
ruff check .
ruff format .

# Type checking
mypy
```

## Architecture

Layered modular monolith under `src/insightflow/`:

- `domain` — business concepts and rules
- `application` — use cases and ports
- `infrastructure` — external adapters
- `presentation` — Windows UI
- `configuration` — settings
- `shared` — small cross-cutting utilities
- `bootstrap` — composition root / startup

See `docs/` for the architectural source of truth.
