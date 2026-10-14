# DEKEN STUDIO AI

Plataforma privada de Grupo Deken (fabricante de ventanas y puertas de PVC Schüco para
profesionales, Santiponce, Sevilla) para producción audiovisual con material real,
dirección creativa asistida por IA y planificación de contenidos.

**Estado:** Sprints 0 y 1 completados y verificados
([Sprint 0](docs/sprints/SPRINT_0_REPORT.md) · [Sprint 1](docs/sprints/SPRINT_1_REPORT.md)).
Funciona: autenticación y roles, auditoría, almacenamiento con URLs firmadas, cola de
trabajos híbrida local/nube, **Biblioteca** (subida multiparte de MP4/MOV, ingesta con
póster, tira, proxy y forma de onda, catálogo, derechos de imagen), **Marca DEKEN**
(logos y tipografías analizados) y **Remotion** como motor de composición en modo
evaluación. Las demás secciones aparecen deshabilitadas con el sprint en que llegan.

> **Licencia de Remotion:** solo desarrollo y evaluación hasta que Grupo Deken verifique
> y regularice la licencia de empresa; los renders comerciales están deshabilitados
> ([ADR 0005](docs/adr/0005-remotion-composition-engine.md)).

## Documentación

| Documento | Contenido |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitectura, capas, decisiones y riesgos |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Sprints 0–5 con criterios verificables |
| [docs/ENVIRONMENT_REVIEW.md](docs/ENVIRONMENT_REVIEW.md) | Entorno, versiones, compatibilidad y licencias |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Modelo de datos actual y previsto |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | API v1, contrato de trabajos v1, timeline v1 |
| [docs/DEPENDENCIES_AND_CREDENTIALS.md](docs/DEPENDENCIES_AND_CREDENTIALS.md) | Credenciales y dependencias externas por sprint |
| [docs/SECURITY.md](docs/SECURITY.md) | Controles, roles, secretos, RGPD |
| [docs/deployment/](docs/deployment) | Desarrollo local, worker en WSL2, servidor |
| [docs/operations/BACKUP_RESTORE.md](docs/operations/BACKUP_RESTORE.md) | Copias y restauración |
| [docs/adr/](docs/adr) | Decisiones de arquitectura |

## Puesta en marcha rápida

Requisitos: Docker, Node 22 + pnpm 10, Python ≥ 3.12 con `uv`, FFmpeg ≥ 6.1.

```bash
make setup                                   # dependencias + infra/.env con secretos aleatorios
make services-up                             # PostgreSQL, Valkey (Redis), SeaweedFS (S3)
make migrate
make admin EMAIL=tu@deken.es NAME="Tu Nombre"
make dev-api      # terminal 1 → http://localhost:8000/api/docs
make dev-web      # terminal 2 → http://localhost:3000
```

Registra un worker en *Configuración → Workers* y arráncalo con
`DEKEN_WORKER_TOKEN=dkw_… make dev-worker`; después lanza el **autotest de render** en
*Configuración → Sistema*. Para el motor Remotion: `make remotion` (renderer, bundle,
navegador y render de evaluación de prueba).

## Estructura

```
apps/web            Next.js 16 + React 19 + TypeScript estricto (interfaz en español)
services/api        FastAPI: API v1, auth, RBAC, auditoría, trabajos, storage
workers/runtime     SDK de workers (solo conexiones salientes, sandbox de FFmpeg)
workers/render      Handlers de render (autotest FFmpeg, Remotion) + renderer Node (remotion/)
workers/analysis    Ingesta de medios con FFmpeg (hash, póster, tira, proxy, forma de onda)
packages/video-compositions  Composiciones Remotion y esquema de la línea de tiempo
packages/shared     Contratos (Python), OpenAPI y tipos TS generados
packages/brand      Tokens de marca DEKEN y pruebas de contraste
infra               Docker Compose, Dockerfiles, migraciones Alembic, scripts
docs                Documentación técnica y operativa
```

## Calidad

```bash
make ci     # lint, tipos, OpenAPI al día, tests, secretos fuera del bundle, E2E
```
