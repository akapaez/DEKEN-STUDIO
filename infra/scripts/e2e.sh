#!/usr/bin/env bash
# E2E de Sprint 0 con servicios reales y una base de datos TEMPORAL:
#   API (uvicorn) + web (next start) + worker real (lo arranca el propio test).
# Requisitos: servicios de infra/docker-compose.yml en marcha, `pnpm build` de apps/web.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source infra/scripts/dev-env.sh

API_PORT="${E2E_API_PORT:-8100}"
WEB_PORT="${E2E_WEB_PORT:-3100}"
DB_NAME="deken_e2e_$(date +%s)"
BUCKET="deken-e2e-$(date +%s)"
ADMIN_EMAIL="admin-e2e@deken.test"
ADMIN_PASSWORD="E2E-$(openssl rand -hex 12)"
LOG_DIR="${E2E_LOG_DIR:-$(mktemp -d)}"
mkdir -p "$LOG_DIR"
PG_ADMIN_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/postgres"

export DEKEN_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/${DB_NAME}"
export DEKEN_S3_BUCKET="$BUCKET"
export DEKEN_ALLOWED_ORIGINS="http://localhost:${WEB_PORT}"
export DEKEN_LOG_JSON=true

# Cada proceso en segundo plano en su propio grupo, para terminar también a sus hijos
# (pnpm → next, uv → uvicorn) y no dejar puertos ocupados.
set -m
pids=()
cleanup() {
  for pid in "${pids[@]:-}"; do kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  psql "$PG_ADMIN_URL" -qc "DROP DATABASE IF EXISTS \"${DB_NAME}\" WITH (FORCE)" >/dev/null || true
  uv run python - <<PY || true
import os, boto3
s3 = boto3.client("s3", endpoint_url=os.environ["DEKEN_S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["DEKEN_S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["DEKEN_S3_SECRET_KEY"], region_name="us-east-1")
for page in s3.get_paginator("list_objects_v2").paginate(Bucket="${BUCKET}"):
    for obj in page.get("Contents", []):
        s3.delete_object(Bucket="${BUCKET}", Key=obj["Key"])
s3.delete_bucket(Bucket="${BUCKET}")
PY
  echo "Logs en ${LOG_DIR}"
}
trap cleanup EXIT

psql "$PG_ADMIN_URL" -qc "CREATE DATABASE \"${DB_NAME}\"" >/dev/null
uv run deken-api migrate
uv run deken-api init-storage
DEKEN_BOOTSTRAP_ADMIN_PASSWORD="$ADMIN_PASSWORD" uv run deken-api create-admin \
  --email "$ADMIN_EMAIL" --name "Administración E2E"

uv run uvicorn deken_api.main:app --port "$API_PORT" >"$LOG_DIR/api.log" 2>&1 &
pids+=($!)
(cd apps/web && DEKEN_API_INTERNAL_URL="http://localhost:${API_PORT}" \
  pnpm exec next start --port "$WEB_PORT" >"$LOG_DIR/web.log" 2>&1) &
pids+=($!)

ready=0
for _ in $(seq 1 60); do
  if curl -fs "http://localhost:${API_PORT}/api/v1/health/ready" >/dev/null &&
     curl -fs -o /dev/null "http://localhost:${WEB_PORT}/login"; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" != 1 ]; then
  echo "La API o la web no arrancaron; revisa ${LOG_DIR}" >&2
  exit 1
fi

cd apps/web
E2E_BASE_URL="http://localhost:${WEB_PORT}" \
E2E_API_URL="http://localhost:${API_PORT}" \
E2E_ADMIN_EMAIL="$ADMIN_EMAIL" \
E2E_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  pnpm exec playwright test "$@"
