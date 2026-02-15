.PHONY: install dev lint format typecheck test test-cov clean build publish check

# Development
install:
	uv sync

dev:
	uv sync --all-extras

# Quality
lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run ty check src

# Testing
test:
	uv run pytest

test-cov:
	uv run pytest --cov=clipmd --cov-report=term-missing --cov-fail-under=89

# Build & Publish
clean:
	rm -rf dist build *.egg-info

build: clean
	uv build

publish: build
	uv publish

# All checks (used by CI and pre-commit)
check: lint typecheck test-cov
