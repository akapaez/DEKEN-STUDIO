#!/bin/sh
# Arranque de la API: migraciones y bucket (idempotentes) y servidor.
set -eu
if [ "${DEKEN_RUN_MIGRATIONS:-true}" = "true" ]; then
  deken-api migrate
  deken-api init-storage
fi
exec uvicorn deken_api.main:app \
  --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips "${DEKEN_FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --no-server-header
