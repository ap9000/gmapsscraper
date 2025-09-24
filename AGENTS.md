# Repository Guidelines

## Project Structure & Module Organization
- `src/`: Main code (CLI entry `main.py`; modules: `scraper.py`, `enricher.py`, `exporter.py`, `database.py`, `hubspot_integration.py`, `utils.py`).
- `tests/`: Pytest suite (e.g., `tests/test_scraper.py`, `tests/test_enricher.py`).
- `config/`: App config (`config.yaml`, `config.example.yaml`). Do not commit secrets.
- `data/`: Exports and cache DB; `logs/`: runtime logs; `proxies.txt`: proxy list.
- `README.md`, `requirements.txt`: usage and dependencies.

## Build, Test, and Development Commands
- Create env and install: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Quick status: `python src/main.py status`
- Run a search: `python src/main.py search "law offices" -l "San Francisco, CA" -m 50`
- Batch from CSV: `python src/main.py batch data/searches/searches.csv --enrich --export csv`
- Run tests: `pytest tests/ -v`
  - Optional coverage (if `pytest-cov` installed): `pytest --cov=src tests/`

## Coding Style & Naming Conventions
- Python 3.10+, PEP 8, 4-space indentation, type hints encouraged.
- Names: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Docstrings: short, actionable one‑liners; prefer explicit return types.
- Logging: use `logging.getLogger(__name__)`; configure via `utils.setup_logging` and `config.logging`.
- Keep changes minimal and consistent; avoid adding deps unless necessary.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-httpx` for HTTP mocking.
- File naming: `tests/test_*.py`; test functions `test_*`.
- Prefer unit tests; mock network I/O (`httpx`) and external APIs.
- Run `pytest` locally before opening PRs; add tests for new behavior and regressions.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject (≤72 chars), explain what/why in body, reference issues (e.g., `Fixes #123`).
- PRs: clear description, scope of change, test evidence (commands/log snippets), and docs updates (`README.md`, `config.example.yaml`) when applicable.
- Ensure tests pass and no secrets are included (`config.yaml`, `.env`, tokens, proxies).

## Security & Configuration Tips
- Never commit real API keys, tokens, or proxy credentials. Use `config/config.yaml` locally and `.env` for env vars.
- Rate limits/budget live in `config.settings`; validate impact via `python src/main.py costs` before large runs.
- Exports go to `data/exports/`; logs to `logs/`. Sanitize samples before sharing.
