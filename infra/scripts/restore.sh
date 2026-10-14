#!/usr/bin/env bash
# Restauración de una copia de DEKEN STUDIO AI.
#
#   infra/scripts/restore.sh --dump backups/db/deken-<fecha>.dump [--objects backups/objects]
#                            [--database NOMBRE] --yes
#
# Restaura la base de datos (en NOMBRE; por defecto la de producción, que se SOBRESCRIBE)
# y vuelve a subir al bucket los objetos que falten. Exige --yes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "${COMPOSE_FILE:-$ROOT/infra/docker-compose.yml}")
DUMP="" OBJECTS="" DATABASE="" CONFIRM=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dump) DUMP="$2"; shift 2 ;;
    --objects) OBJECTS="$2"; shift 2 ;;
    --database) DATABASE="$2"; shift 2 ;;
    --yes) CONFIRM=1; shift ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
done
[ -f "$DUMP" ] || { echo "Falta --dump con un fichero existente" >&2; exit 2; }
[ "$CONFIRM" = 1 ] || { echo "La restauración sobrescribe datos: repite con --yes" >&2; exit 2; }

# shellcheck disable=SC1091
source "$ROOT/infra/scripts/dev-env.sh"
DATABASE="${DATABASE:-${POSTGRES_DB:-deken}}"

"${COMPOSE[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d postgres -qc \
  "SELECT 1 FROM pg_database WHERE datname = '$DATABASE'" | grep -q 1 ||
  "${COMPOSE[@]}" exec -T postgres createdb -U "$POSTGRES_USER" "$DATABASE"
"${COMPOSE[@]}" exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$DATABASE" \
  --clean --if-exists --no-owner --exit-on-error < "$DUMP"
echo "Base de datos '$DATABASE' restaurada desde $DUMP"

if [ -n "$OBJECTS" ]; then
  (cd "$ROOT" && uv run deken-api storage-restore --src "$OBJECTS")
fi
