.PHONY: setup check lint fmt types test schemas

setup:            ## install dependencies from the lockfile
	uv sync --locked

check: lint types test schemas-check   ## everything CI runs

lint:
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts

fmt:
	uv run ruff check --fix src tests scripts
	uv run ruff format src tests scripts

types:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing

schemas:          ## regenerate schemas/ and docs/capabilities.md after a contract change
	uv run python scripts/export_schemas.py

schemas-check:
	uv run python scripts/export_schemas.py --check
