#!/usr/bin/env bash
# Copia de seguridad de DEKEN STUDIO AI: base de datos (pg_dump, formato custom) y
# réplica incremental del almacenamiento de objetos. Pensado para cron diario.
#
#   infra/scripts/backup.sh [DESTINO]          (por defecto ./backups)
#
# Variables: BACKUP_KEEP (días de dumps a conservar, 14), COMPOSE_FILE.
# El destino debe replicarse fuera del servidor (ver docs/operations/BACKUP_RESTORE.md).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$(realpath -m "${1:-$ROOT/backups}")"
KEEP="${BACKUP_KEEP:-14}"
COMPOSE=(docker compose -f "${COMPOSE_FILE:-$ROOT/infra/docker-compose.yml}")
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p "$DEST/db" "$DEST/objects"

# shellcheck disable=SC1091
source "$ROOT/infra/scripts/dev-env.sh"

DUMP="$DEST/db/deken-$STAMP.dump"
"${COMPOSE[@]}" exec -T postgres pg_dump -U "$POSTGRES_USER" -d "${POSTGRES_DB:-deken}" \
  --format=custom --compress=6 --no-owner > "$DUMP"
# Valida que el dump es legible antes de darlo por bueno.
"${COMPOSE[@]}" exec -T postgres pg_restore --list < "$DUMP" > /dev/null

(cd "$ROOT" && uv run deken-api storage-backup --dest "$DEST/objects") > "$DEST/objects-$STAMP.json"

REVISION="$("${COMPOSE[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-deken}" \
  -tAc "SELECT version_num FROM alembic_version")"
cat > "$DEST/db/deken-$STAMP.json" <<JSON
{
  "created_at": "$STAMP",
  "database": "${POSTGRES_DB:-deken}",
  "migration": "$REVISION",
  "dump": "$(basename "$DUMP")",
  "dump_sha256": "$(sha256sum "$DUMP" | cut -d' ' -f1)",
  "objects": $(cat "$DEST/objects-$STAMP.json")
}
JSON
rm -f "$DEST/objects-$STAMP.json"

find "$DEST/db" -name 'deken-*' -type f -mtime +"$KEEP" -delete
echo "Copia completada: $DUMP"
