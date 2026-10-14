# Desarrollo local

Requisitos: Docker (con Compose v2), Node 22 + pnpm 10, Python 3.12+ con `uv`, FFmpeg ≥ 6.1.

```bash
make setup          # uv sync + pnpm install + infra/.env con secretos aleatorios
make services-up    # PostgreSQL 16, Valkey 8 (Redis), SeaweedFS (S3)
make migrate        # migraciones + bucket
make admin EMAIL=tu@deken.es NAME="Tu Nombre"   # pide la contraseña

make dev-api        # http://localhost:8000/api/docs
make dev-web        # http://localhost:3000
```

Worker local (otra terminal): crea un worker en *Configuración → Workers*, copia el token y:

```bash
DEKEN_WORKER_TOKEN=dkw_... make dev-worker
```

En *Configuración → Sistema* lanza el **autotest de render** para comprobar la cadena
completa (worker → FFmpeg → almacenamiento → verificación → vista previa → descarga).

### Motor Remotion (Sprint 1)

```bash
make remotion   # esquema al día, renderer, bundle de composiciones, Chrome Headless Shell
                # (descarga desde remotion.media) y render de evaluación de prueba
```

Si la red no permite la descarga del navegador, apunta `DEKEN_REMOTION_BROWSER` (en
`infra/.env`) a un Chrome Headless Shell existente y comprueba con
`uv run deken-remotion-check`. El worker solo registra los handlers de Remotion si el
motor está disponible; el estado aparece en *Configuración → Sistema → Remotion*.
Remotion funciona en modo **evaluación** (ver ADR 0005): renders con marca de agua en
`evaluation/`, nunca comerciales.

Para ver o ajustar las composiciones: `pnpm --filter @deken/video-compositions studio`
(Remotion Studio, solo desarrollo).

### Biblioteca (Sprint 1)

La subida va directa del navegador al almacenamiento: el origen de la web debe estar en
`S3_ALLOWED_ORIGINS` (CORS de SeaweedFS; por defecto `http://localhost:3000` y el de E2E,
`http://localhost:3100`) y el almacenamiento en `DEKEN_MEDIA_ORIGINS` de la web (CSP).
El worker debe atender la cola `analysis` para la ingesta.

## Todo en contenedores

```bash
make images
docker compose -f infra/docker-compose.yml --profile app up -d
DEKEN_WORKER_TOKEN=dkw_... docker compose -f infra/docker-compose.yml --profile worker up -d
```

## Pruebas

```bash
make lint typecheck       # ruff, mypy --strict, eslint, tsc --strict
make test                 # pytest (integración real) + vitest
make check-secrets        # ningún secreto en el build web
make e2e                  # Playwright con API, web y worker reales (BD temporal)
make ci                   # todo lo anterior
```

Los tests de integración usan una base de datos temporal en el mismo PostgreSQL, la BD 15
de Redis y un bucket temporal; se borran al terminar.
