# DEKEN STUDIO AI — tareas comunes. `make help` para ver la lista.
SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml
DEV_ENV := source infra/scripts/dev-env.sh

.PHONY: help setup env services-up services-down services-ps migrate admin dev-api dev-web \
	dev-worker lint typecheck test test-py test-web e2e build check-generated check-secrets \
	generate-api images backup ci

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup: env ## Instala dependencias Python (uv) y JS (pnpm)
	uv sync
	pnpm install --frozen-lockfile

env: ## Crea infra/.env con secretos aleatorios si no existe
	@if [ ! -f infra/.env ]; then \
	  sed -e "s|^DEKEN_SECRET_KEY=.*|DEKEN_SECRET_KEY=$$(openssl rand -base64 48 | tr -d '\n/+=')|" \
	      -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$(openssl rand -hex 16)|" \
	      -e "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$$(openssl rand -hex 16)|" \
	      -e "s|^S3_ACCESS_KEY=.*|S3_ACCESS_KEY=$$(openssl rand -hex 10)|" \
	      -e "s|^S3_SECRET_KEY=.*|S3_SECRET_KEY=$$(openssl rand -hex 20)|" \
	      infra/.env.example > infra/.env; \
	  chmod 600 infra/.env; echo "infra/.env creado con secretos aleatorios"; \
	else echo "infra/.env ya existe"; fi

services-up: env ## Arranca PostgreSQL, Redis (Valkey) y SeaweedFS
	$(COMPOSE) up -d --wait postgres redis seaweedfs
	$(COMPOSE) ps

services-down: ## Para los servicios (los datos se conservan en volúmenes)
	$(COMPOSE) down

services-ps: ## Estado de los servicios
	$(COMPOSE) ps

migrate: ## Aplica migraciones y crea el bucket
	$(DEV_ENV) && uv run deken-api migrate && uv run deken-api init-storage

admin: ## Crea el primer administrador (EMAIL=... NAME=...)
	$(DEV_ENV) && uv run deken-api create-admin --email "$(EMAIL)" --name "$(NAME)"

dev-api: ## API en modo desarrollo (http://localhost:8000/api/docs)
	$(DEV_ENV) && uv run uvicorn deken_api.main:app --reload --port 8000

dev-web: ## Web en modo desarrollo (http://localhost:3000)
	cd apps/web && DEKEN_API_INTERNAL_URL=http://localhost:8000 pnpm dev

dev-worker: ## Worker local (DEKEN_WORKER_TOKEN=... make dev-worker)
	DEKEN_API_URL=http://localhost:8000 uv run deken-worker run

generate-api: ## Regenera openapi.json y los tipos TS
	pnpm generate:api

check-generated: ## Falla si OpenAPI/tipos TS no están al día
	pnpm --filter @deken/shared check-generated

lint: ## Ruff + ESLint
	uv run ruff check .
	uv run ruff format --check .
	pnpm --filter @deken/web lint

typecheck: ## mypy estricto + tsc estricto
	uv run mypy packages/shared/python/src services/api/src workers/runtime/src workers/render/src
	pnpm -r typecheck

test-py: ## Tests Python (integración contra los servicios de infra)
	$(DEV_ENV) && uv run pytest

test-web: ## Tests unitarios web y marca
	pnpm -r test

test: test-py test-web ## Todos los tests salvo E2E

build: ## Build de producción de la web
	cd apps/web && pnpm build

check-secrets: build ## Comprueba que ningún secreto acaba en el build web
	cd apps/web && pnpm check-secrets

e2e: build ## E2E con servicios reales y BD temporal
	infra/scripts/e2e.sh

images: ## Construye las imágenes Docker
	docker build -f infra/docker/api.Dockerfile -t deken/api:dev .
	docker build -f infra/docker/worker.Dockerfile -t deken/worker:dev .
	docker build -f infra/docker/web.Dockerfile -t deken/web:dev .

backup: ## Copia de seguridad (BD + objetos) en ./backups
	infra/scripts/backup.sh

ci: lint typecheck check-generated test check-secrets e2e ## Lo mismo que CI
