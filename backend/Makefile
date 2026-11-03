.DEFAULT_GOAL := help
.PHONY: help dev up down logs test test-all lint fmt check clean reset

help:  ## List the targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

dev:  ## Install dependencies and create .env
	uv sync --all-extras --group dev
	@test -f .env || cp .env.example .env

up:  ## Start local services
	docker compose up -d
	@echo "MinIO console: http://localhost:9001"

down:  ## Stop local services (data is kept)
	docker compose down

logs:  ## Follow service logs
	docker compose logs -f

test:  ## Unit tests (no services needed)
	uv run pytest -m "not integration"

test-all: up  ## All tests, including integration
	uv run pytest

lint:  ## Check format and lint
	uv run ruff format --check .
	uv run ruff check .

fmt:  ## Format and apply safe lint fixes
	uv run ruff format .
	uv run ruff check --fix .

check: lint test  ## What CI runs

clean:  ## Remove caches
	rm -rf .pytest_cache .ruff_cache .coverage dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

reset:  ## Delete all local service data and start again
	docker compose down -v
	docker compose up -d
