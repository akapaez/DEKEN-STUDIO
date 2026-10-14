# Informe de Sprint 0 — Infraestructura, base de datos, almacenamiento y autenticación

Fecha: 2026-10-14 · Estado: **criterios de aceptación cumplidos** (salvo la ejecución en
GitHub Actions, que se verá al primer push; ver §3).

Todas las pruebas se han ejecutado contra servicios reales (PostgreSQL 16, Valkey 8,
SeaweedFS, FFmpeg/ffprobe), sin simulaciones. Los únicos datos sintéticos son los del
autotest de render y los ficheros de prueba, etiquetados como tales.

## 1. Criterios de aceptación

| ID | Resultado | Evidencia |
|---|---|---|
| S0-01 Servicios sanos | ✅ | `make services-up` → postgres, redis (Valkey) y seaweedfs `healthy`. Stack completo en contenedores (`--profile app` y `--profile worker`) también sano. |
| S0-02 Migraciones | ✅ | `tests/migrations/test_migrations.py`: upgrade → downgrade → upgrade y `alembic check` sin deriva. |
| S0-03 Salud | ✅ | `test_live_and_ready`, `test_ready_reports_failures` (storage caído ⇒ `error`/503; Redis caído ⇒ `degraded`). |
| S0-04 Autenticación | ✅ | 12 tests en `test_auth.py`: cookies HttpOnly/SameSite, error genérico, logout revoca, caducidad absoluta e inactividad, desactivación inmediata, cambio de contraseña revoca otras sesiones. |
| S0-05 Roles | ✅ | `test_permission_matrix` (4 roles × 15 rutas). |
| S0-06 CSRF/Origen | ✅ | `test_csrf_token_required_for_unsafe_methods`, `test_login_rejects_foreign_origin`. |
| S0-07 Limitación de login | ✅ | `test_login_rate_limit`: el intento 11 → 429 con `Retry-After` y evento `denied`. |
| S0-08 Auditoría | ✅ | Eventos de login OK/KO, alta y cambio de rol, alta/revocación de worker, denegaciones; *trigger* de solo inserción probado. |
| S0-09 Storage | ✅ | Subida/descarga firmadas, caducidad (403 tras expirar), firma inválida al alterar la clave, nombres de descarga saneados, claves sin entrada de usuario. |
| S0-10 Contrato de trabajos | ✅ | 18 tests en `test_job_contract.py`: claim exclusivo con 6 workers concurrentes, long-poll despertado por Redis, lease renovado, lease perdido (409), reaper reencola y agota intentos, backoff, fallo no reintentable + reintento manual, cancelación en cola y en curso, salidas no previstas rechazadas, verificación fallida (no es vídeo, SHA-256, tamaño, resolución 16:9). |
| S0-11 Render real | ✅ | `test_render_selftest_end_to_end`: API por HTTP + worker real + FFmpeg ⇒ MP4 descargado con ffprobe: H.264 1080×1920 `yuv420p` 30/1 fps, 60 fotogramas, AAC 48 kHz, 2,00 s, decodificación completa sin errores; directorio temporal borrado. `test_worker_honours_cancellation`: cancelación en mitad del render. |
| S0-12 Web (E2E) | ✅ | `infra/scripts/e2e.sh` → 8/8 en Playwright: redirección sin sesión, error genérico, dashboard con estado real y navegación honesta (2 enlaces + 8 secciones deshabilitadas), tema claro/oscuro persistente, alta de usuario, registro de worker + worker real + autotest verificado + descarga + ffprobe, permisos de editor, auditoría y logout. |
| S0-13 Secretos | ✅ | `make check-secrets`: 5 secretos buscados en 3.678 ficheros del build; ninguno aparece. |
| S0-14 Backup | ✅ | `infra/scripts/backup.sh` + `restore.sh` en BD y bucket nuevos: recuentos idénticos y SHA-256 idéntico de todos los objetos. |
| S0-15 Calidad | ✅ local | `ruff`, `ruff format`, `mypy --strict` (55 ficheros), `tsc --strict`, `eslint`, `pytest` (125), `vitest` (22), Playwright (8). |

## 2. Resultados de la verificación

```
uv run pytest                      125 passed
pnpm -r test                       brand 5 passed · web 17 passed
infra/scripts/e2e.sh               8 passed
make lint typecheck check-generated   sin errores; OpenAPI y tipos TS al día
make check-secrets                 OK
docker build (api, worker, web)    OK; stack en contenedores: autotest completed
```

Incidencias detectadas y corregidas por las propias pruebas:

- El long-poll de `claim` accedía a atributos ORM expirados tras una transacción vacía
  (`MissingGreenlet`). Corregido sin releer el ORM entre iteraciones.
- La verificación de integridad no detectaba un MP4 con datos corruptos. Ahora usa
  `-err_detect explode` y cualquier error de decodificación invalida el fichero.
- Contraste insuficiente (4,30:1) de las etiquetas sobre la superficie elevada del tema
  oscuro. Ajustado el neutro derivado a `#1A1D1E` (4,61:1).
- SeaweedFS se quedaba sin volúmenes con muchos buckets de prueba: límite de volúmenes
  configurable y limpieza de buckets temporales en los tests.
- Los logs del worker incluían URLs firmadas (vía httpx): silenciados.

## 3. Pendiente y fuera de alcance

- **CI en GitHub Actions**: el workflow `.github/workflows/ci.yml` reproduce lo anterior;
  se valida en el primer push.
- Las secciones Director IA, Biblioteca, Productor, Editor, Calendario y Marca DEKEN
  aparecen deshabilitadas con su sprint.
- `workers/analysis` es solo un marcador documentado (Sprint 1).
- Remotion no se usa (licencia de empresa pendiente de decisión de DEKEN).

## 4. Dependencias para empezar Sprint 1

1. Grabaciones reales de DEKEN (MP4/MOV) en el servidor de pruebas.
2. Logos oficiales y `.ttf` de Montserrat de `Deken-Recursos`.
3. Criterio sobre consentimientos de imagen de las personas que aparecen.
4. Decisión sobre el servidor de despliegue (o seguir en local con WSL2).
