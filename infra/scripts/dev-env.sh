#!/usr/bin/env bash
# Exporta las variables DEKEN_* para ejecutar API/worker en el host contra los servicios
# de infra/docker-compose.yml.   Uso:  source infra/scripts/dev-env.sh
_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ ! -f "$_root/infra/.env" ]; then
  echo "Falta infra/.env (cp infra/.env.example infra/.env)" >&2
  return 1 2>/dev/null || exit 1
fi
set -a
# shellcheck disable=SC1091
. "$_root/infra/.env"
set +a
export DEKEN_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-deken}"
export DEKEN_REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:${REDIS_PORT:-6379}/0"
export DEKEN_S3_ENDPOINT_URL="http://localhost:${S3_PORT:-8333}"
export DEKEN_S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-http://localhost:${S3_PORT:-8333}}"
export DEKEN_S3_WORKER_ENDPOINT_URL="http://localhost:${S3_PORT:-8333}"
export DEKEN_S3_ACCESS_KEY="$S3_ACCESS_KEY"
export DEKEN_S3_SECRET_KEY="$S3_SECRET_KEY"
export DEKEN_S3_BUCKET="${DEKEN_S3_BUCKET:-${S3_BUCKET:-deken-studio}}"
export DEKEN_LOG_JSON="${DEKEN_LOG_JSON:-false}"
unset _root

# Tests de integración contra los mismos servicios (BD temporal propia, Redis BD 15).
export DEKEN_TEST_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/postgres"
export DEKEN_TEST_REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:${REDIS_PORT:-6379}/15"
export DEKEN_TEST_S3_ENDPOINT_URL="http://localhost:${S3_PORT:-8333}"
export DEKEN_TEST_S3_ACCESS_KEY="$S3_ACCESS_KEY"
export DEKEN_TEST_S3_SECRET_KEY="$S3_SECRET_KEY"
