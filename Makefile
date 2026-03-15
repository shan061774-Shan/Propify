SHELL := /bin/bash
PYTHON ?= /Users/shan/rental_system/venv/bin/python
ALEMBIC ?= /Users/shan/rental_system/venv/bin/alembic
DOCKER_COMPOSE ?= docker compose

.PHONY: help up down logs rebuild migrate current snowflake-migrate api ui stop-ui stop-api

help:
	@echo "Available targets:"
	@echo "  make up                 # Start API + UI with Docker Compose"
	@echo "  make down               # Stop Docker Compose services"
	@echo "  make logs               # Tail Docker Compose logs"
	@echo "  make rebuild            # Rebuild and restart Docker Compose services"
	@echo "  make migrate            # Alembic upgrade head (active DB)"
	@echo "  make current            # Show current Alembic revision"
	@echo "  make snowflake-migrate  # Run SQLite -> Snowflake data migration script"
	@echo "  make api                # Run FastAPI locally"
	@echo "  make ui                 # Run Streamlit locally"
	@echo "  make stop-api           # Kill process on port 8000"
	@echo "  make stop-ui            # Kill process on port 8502"

up:
	$(DOCKER_COMPOSE) up --build -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f --tail=200

rebuild:
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) up --build -d

migrate:
	$(ALEMBIC) upgrade head

current:
	$(ALEMBIC) current

snowflake-migrate:
	SNOWFLAKE_URL="$${SNOWFLAKE_URL:-$${PROPIFY_DATABASE_URL}}" $(PYTHON) scripts/migrate_sqlite_to_snowflake.py

api:
	$(PYTHON) -m uvicorn api.main:app --host 127.0.0.1 --port 8000

ui:
	$(PYTHON) -m streamlit run ui_admin/app.py

stop-api:
	lsof -ti tcp:8000 | xargs -r kill -9

stop-ui:
	lsof -ti tcp:8502 | xargs -r kill -9
