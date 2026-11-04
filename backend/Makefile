.DEFAULT_GOAL := help
.PHONY: help dev up down logs migrate revision run practice test test-all lint fmt check clean reset

API_PORT ?= 8000

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

migrate:  ## Apply database migrations
	uv run --extra api alembic upgrade head

revision:  ## New migration from model changes: make revision m="add x"
	uv run --extra api alembic revision --autogenerate -m "$(m)"

run:  ## Start the API with reload (API_PORT=8000)
	uv run --all-extras uvicorn server.main:app --reload --host 0.0.0.0 --port $(API_PORT)

practice:  ## Full stack for phone testing: Docker, API and agent
	API_PORT=$(API_PORT) ./scripts/dev.sh

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
