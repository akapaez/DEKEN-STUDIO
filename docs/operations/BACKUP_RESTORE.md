# Copias de seguridad y restauración

## Qué se copia

| Elemento | Cómo | Frecuencia |
|---|---|---|
| Base de datos | `pg_dump` formato custom, validado con `pg_restore --list`, manifiesto con SHA-256 y revisión de migración | Diaria (cron) |
| Objetos (originales, derivados, renders, marca) | Réplica incremental del bucket (`deken-api storage-backup`) | Diaria |
| `infra/.env` / secretos | Gestor de secretos de la empresa (no en la copia) | Al cambiar |

Los originales son inmutables, así que la réplica incremental nunca pierde versiones.

```bash
infra/scripts/backup.sh /srv/backups/deken          # BACKUP_KEEP=14 días por defecto
# cron: 15 3 * * * cd /srv/deken-studio && infra/scripts/backup.sh /srv/backups/deken >> /var/log/deken-backup.log 2>&1
```

El directorio de copias debe replicarse **fuera del servidor** (NAS, otro proveedor S3,
disco externo cifrado).

## Restaurar

```bash
# 1. Base de datos (en una BD nueva para comprobar, o en la de producción con la app parada)
infra/scripts/restore.sh --dump /srv/backups/deken/db/deken-<fecha>.dump \
    --database deken_restaurada --yes
# 2. Objetos que falten en el bucket
infra/scripts/restore.sh --dump ... --objects /srv/backups/deken/objects --yes
```

Tras restaurar en producción: `deken-api migrate` (por si la copia es de una versión
anterior) y `deken-api check`.

## Prueba realizada (Sprint 0)

Copia de la BD de desarrollo y del bucket; restauración en una BD y un bucket nuevos;
recuentos idénticos (`users`, `jobs`, `audit_events`, `stored_objects`, revisión `0001`)
y SHA-256 idéntico de todos los objetos. Ver `docs/sprints/SPRINT_0_REPORT.md`.

Simulacro completo con tiempos (RTO/RPO) previsto en Sprint 5.
