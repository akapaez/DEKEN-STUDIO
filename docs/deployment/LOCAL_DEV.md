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
