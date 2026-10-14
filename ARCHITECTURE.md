# DEKEN STUDIO AI — Arquitectura

> Estado: **vigente para V1**. Documento vivo: cualquier cambio de arquitectura se
> registra aquí y, si es una decisión relevante, en `docs/adr/`.
>
> Documentos relacionados:
> [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) ·
> [docs/ENVIRONMENT_REVIEW.md](docs/ENVIRONMENT_REVIEW.md) ·
> [docs/DATA_MODEL.md](docs/DATA_MODEL.md) ·
> [docs/CONTRACTS.md](docs/CONTRACTS.md) ·
> [docs/DEPENDENCIES_AND_CREDENTIALS.md](docs/DEPENDENCIES_AND_CREDENTIALS.md) ·
> [docs/SECURITY.md](docs/SECURITY.md)

## 1. Propósito

DEKEN STUDIO AI es una plataforma **privada** de Grupo Deken (fabricante de ventanas y
puertas de PVC Schüco para profesionales, Santiponce, Sevilla) que une en un mismo
sistema:

1. Producción audiovisual automática a partir de grabaciones reales de DEKEN.
2. Edición manual sobre una línea de tiempo estructurada.
3. Dirección creativa asistida por IA, anclada en una base de conocimiento verificada.
4. Planificación de campañas y calendario editorial.
5. Gestión de identidad de marca.
6. (V2) Publicación en redes vía APIs oficiales, analítica y leads.

### Principios no negociables

| Principio | Consecuencia técnica |
|---|---|
| Nada simulado | Un trabajo solo es `completed` si su salida existe en el almacenamiento y supera la verificación (ffprobe en servidor). No hay datos de ejemplo en producción. |
| Originales intocables | Los originales se guardan con clave generada por el servidor, nunca se sobrescriben ni se procesan in situ; todo derivado es un objeto nuevo. |
| Afirmaciones verificadas | La IA solo puede afirmar datos técnicos presentes en la base de conocimiento, con cita a la fuente. Sin IA configurada, la plataforma funciona en modo manual y lo dice. |
| Aprobación humana | Ningún contenido pasa a "publicable" sin aprobación de un usuario con rol `reviewer` o `admin`. La publicación automática no existe en V1. |
| Público profesional | Mensajes orientados a instaladores, distribuidores, constructoras y carpinterías. DEKEN no se posiciona como instalador para particulares. |
| Honestidad de la interfaz | Las secciones no implementadas aparecen deshabilitadas con su sprint; nunca como operativas. |

## 2. Contexto

```mermaid
flowchart LR
    subgraph Usuarios internos
      A[Administrador]
      E[Editor / productor]
      R[Revisor / aprobador]
      V[Lector]
    end

    subgraph Plataforma["DEKEN STUDIO AI (servidor)"]
      WEB[apps/web<br/>Next.js]
      API[services/api<br/>FastAPI]
      PG[(PostgreSQL)]
      RD[(Redis)]
      S3[(Almacenamiento<br/>compatible S3)]
    end

    subgraph Procesamiento
      WL[Worker local<br/>Windows/WSL2]
      WC[Worker nube<br/>futuro]
    end

    AI[(Proveedor IA<br/>opcional)]
    SOC[(Redes sociales<br/>V2, OAuth oficial)]

    A & E & R & V -->|HTTPS| WEB
    WEB -->|/api/v1 same-origin| API
    API --> PG
    API --> RD
    API --> S3
    WL -->|HTTPS saliente<br/>token de worker| API
    WC -.->|mismo contrato| API
    WL -->|URLs firmadas| S3
    API -.->|claves solo en servidor| AI
    API -.->|V2| SOC
```

El navegador **solo** habla con `apps/web` y con `/api/v1` (mismo origen) y descarga
o sube ficheros mediante URLs firmadas de corta duración. Ninguna credencial de
proveedor llega al navegador.

## 3. Separación de responsabilidades

La brief exige separar estrictamente seis capas. Así se materializan:

| Capa | Dónde vive | Regla |
|---|---|---|
| Interfaz | `apps/web` | Sin lógica de negocio: renderiza, valida formularios para UX y llama a la API tipada. Nunca decide permisos (solo oculta lo que la API denegaría). |
| Lógica de negocio | `services/api/src/deken_api/services/` | Casos de uso puros sobre la sesión de BD y puertos (storage, cola, IA). No conoce HTTP. |
| Servicios de IA | `services/api/src/deken_api/ai/` (Sprint 2) | Puerto `AIProvider` con implementaciones intercambiables; recibe contexto de la base de conocimiento y devuelve contenido con citas. |
| Procesamiento audiovisual | `workers/*` | Procesos separados que solo hablan con la API por HTTPS. FFmpeg se invoca con listas de argumentos, nunca con shell. |
| Persistencia | `services/api/src/deken_api/db/` + `infra/migrations/` | SQLAlchemy 2 (async) + Alembic. Solo la API toca PostgreSQL. |
| Integraciones externas | `services/api/src/deken_api/integrations/` | Storage S3, Redis, ffprobe, (V2) redes sociales. Cada una tras una interfaz con comprobación de salud. |

Las rutas HTTP (`api/v1/*`) son adaptadores finos: validan con Pydantic, comprueban
permisos y delegan en `services/`.

## 4. Estructura del monorepo

```
apps/web/                 Next.js (App Router) + React + TypeScript estricto
services/api/             FastAPI: API v1, auth, RBAC, auditoría, trabajos, storage
workers/runtime/          SDK común de workers (cliente HTTP, bucle, sandbox de procesos)
workers/render/           Handlers de render (FFmpeg; Remotion opcional, ver §10)
workers/analysis/         Handlers de análisis: ffprobe, miniaturas, segmentos, transcripción
packages/shared/python/   Contratos Python compartidos (contrato de trabajos v1, límites de medios)
packages/shared/ts/       Tipos TS generados desde OpenAPI + constantes compartidas
packages/shared/openapi/  openapi.json generado (versionado en git, comprobado en CI)
packages/brand/           Tokens de marca (CSS/TS), tipografías, reglas de uso
infra/                    Docker Compose, Dockerfiles, migraciones Alembic, scripts de backup
docs/                     Arquitectura detallada, contratos, despliegue, manuales
```

Herramientas: **uv** (workspace Python) y **pnpm** (workspace JS). Un único `Makefile`
en la raíz orquesta tareas comunes.

## 5. Stack y justificación

| Pieza | Elección | Motivo |
|---|---|---|
| Web | Next.js 16 + React 19 + TS 5.9 estricto | Requerido por la brief. App Router, rewrites a la API en desarrollo. |
| Estado de servidor en web | TanStack Query 5 | Caché, reintentos y estados de carga/error explícitos. |
| Cliente API | `openapi-fetch` + tipos generados por `openapi-typescript` | Un único origen de verdad (OpenAPI de FastAPI); CI falla si los tipos no están al día. |
| API | FastAPI + Pydantic 2 + SQLAlchemy 2.x async + asyncpg | Tipado, OpenAPI automática, I/O asíncrona (long-poll de workers). |
| Migraciones | Alembic, en `infra/migrations` | Versionadas, reversibles, comprobadas en CI (`alembic check`). |
| Contraseñas | argon2id (`argon2-cffi`) | Recomendación OWASP. |
| Sesiones | Cookie opaca + tabla `sessions` (no JWT) | Revocación inmediata (logout, desactivación de usuario), sin refresh tokens en el navegador. |
| Cola | PostgreSQL como fuente de verdad + Redis (Valkey 8, BSD) como señal | Estado durable y auditable; `SKIP LOCKED` para reparto; Redis despierta a los workers en long-poll y limita intentos de login. Si Redis cae, los workers siguen funcionando por sondeo. |
| Almacenamiento | S3 (boto3). Dev: **SeaweedFS** (Apache-2.0) | Compatible S3, licencia permisiva. MinIO descartado por cambio de distribución/licencia (ver `docs/ENVIRONMENT_REVIEW.md`). Producción: cualquier S3 (AWS, Cloudflare R2, Wasabi, SeaweedFS propio). |
| Vídeo | FFmpeg/ffprobe (CLI) | Estándar de facto, H.264/AAC, filtros de reencuadre, subtítulos (libass) y detección (escenas, silencio, negro, desenfoque). |
| Motion graphics | Remotion (opcional, **requiere licencia de empresa**) | Ver §10. V1 no depende de Remotion. |
| Transcripción | faster-whisper (MIT) en el worker local | Privacidad (audio no sale del equipo), sin coste por minuto. Sprint 1/4. |
| Logs | structlog JSON + `X-Request-ID` | Correlación API ↔ worker ↔ trabajo. |
| Tipografía | Montserrat (OFL-1.1), IBM Plex Mono (OFL-1.1) vía `@fontsource`, servidas localmente | Sin peticiones a Google en tiempo de ejecución (RGPD). |

## 6. Persistencia

### 6.1 PostgreSQL (fuente de verdad)
Usuarios, sesiones, auditoría, workers, trabajos y sus eventos, objetos almacenados,
y — desde Sprint 1 — activos, proyectos, líneas de tiempo, guiones, campañas y
calendario. Modelo completo en [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

### 6.2 Redis (efímero)
- `jobs:wake:<cola>`: señal para despertar long-polls de workers.
- `rl:login:*`: ventanas de limitación de intentos de login.
- Nada en Redis es imprescindible para la integridad: si se pierde, se reconstruye.

### 6.3 Almacenamiento de objetos
Un bucket por entorno (`deken-studio` por defecto) con prefijos:

| Prefijo | Contenido | Política |
|---|---|---|
| `originals/` | Ficheros importados tal cual | Inmutables. Clave `originals/<uuid>/<sha256>.<ext>`. Nunca se emite una URL de subida para una clave existente. |
| `derived/` | Miniaturas, proxies, waveforms, transcripciones | Regenerables desde originales. |
| `renders/` | Exportaciones MP4 finales | Solo tras verificación. |
| `brand/` | Logos y recursos de marca oficiales | Subidos por admin. |
| `system/` | Pruebas técnicas del sistema (autotest de render) | Datos sintéticos **etiquetados**; nunca se mezclan con contenido. |

Las claves **siempre** las genera el servidor (UUID + hash). Los nombres de fichero
del usuario se guardan como metadato saneado, nunca como ruta.

## 7. Contrato de trabajos (híbrido local / nube)

Contrato completo en [docs/CONTRACTS.md §3](docs/CONTRACTS.md). Resumen:

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> processing: claim (lease)
    queued --> cancelled: cancel
    processing --> completed: complete + verificación OK
    processing --> failed: fail no reintentable / verificación KO / reintentos agotados
    processing --> queued: fail reintentable o lease expirado (attempts < max, con backoff)
    processing --> cancelled: cancel solicitado + ack del worker (o lease expirado)
    failed --> queued: retry manual (nuevo intento)
    completed --> [*]
    cancelled --> [*]
```

- **Solo conexiones salientes desde el worker.** El worker hace long-poll a
  `POST /api/v1/worker/jobs/claim` con su token. No necesita puertos abiertos, VPN
  ni credenciales S3: recibe URLs firmadas para leer entradas y pide URLs firmadas
  para subir salidas.
- **Lease**: cada trabajo reclamado tiene `lease_expires_at`; el worker lo renueva al
  informar progreso. Si el worker muere, el *reaper* de la API lo devuelve a la cola
  (o lo marca `failed` si agotó intentos).
- **Cancelación cooperativa**: la API marca `cancel_requested`; el worker lo ve en la
  respuesta de progreso, mata el proceso FFmpeg y confirma.
- **Verificación de salida**: al completar, la API comprueba que cada objeto existe,
  que tamaño y SHA-256 coinciden con lo declarado, y para vídeo ejecuta **ffprobe en el
  servidor** contra el objeto almacenado y lo compara con la especificación pedida
  (códec, resolución, fps, duración, pista de audio). Si falla, el trabajo es `failed`
  con `output_verification_failed`.
- **Trazabilidad**: cada transición, reintento, error y salida queda en `job_events`.
- **Versionado**: cabecera `X-Deken-Job-Contract: 1`; la API rechaza workers con una
  versión incompatible.

Un worker en la nube usa **exactamente** el mismo protocolo; solo cambia dónde corre.

## 8. Despliegue

| Entorno | Composición |
|---|---|
| Desarrollo | `infra/docker-compose.yml` con PostgreSQL 16, Valkey 8 (compatible Redis) y SeaweedFS; API, web y worker en el host (`make dev`) o en contenedores (`--profile app`). |
| Servidor V1 | Mismo Compose detrás de un proxy TLS (Caddy/Traefik) que enruta `/api` → API y `/` → web. Almacenamiento S3 gestionado o SeaweedFS con volumen respaldado. |
| Worker local | Windows 11 + WSL2 (Ubuntu) con FFmpeg, o Docker Desktop. Solo necesita `DEKEN_API_URL` y `DEKEN_WORKER_TOKEN`. Guía: [docs/deployment/WORKER_WSL2.md](docs/deployment/WORKER_WSL2.md). |
| Worker nube (futuro) | Misma imagen `infra/docker/worker.Dockerfile` en cualquier proveedor con GPU/CPU. |

## 9. Seguridad (resumen)

Detalle y matriz de permisos en [docs/SECURITY.md](docs/SECURITY.md).

- **Autenticación**: email + contraseña (argon2id). Sesión en cookie `HttpOnly`,
  `SameSite=Lax`, `Secure` en producción; caducidad por inactividad y absoluta.
- **CSRF**: doble envío (cookie `deken_csrf` + cabecera `X-CSRF-Token`, derivado por
  HMAC de la sesión) y comprobación de `Origin` en métodos no seguros.
- **Roles**: `admin`, `editor`, `reviewer`, `viewer`, mapeados a permisos finos;
  la API comprueba permisos en cada ruta.
- **Workers**: token `dkw_…` de 256 bits, guardado como hash, revocable, limitado al
  protocolo de workers.
- **Secretos**: solo por variables de entorno o ficheros (`/run/secrets`); nunca en el
  repositorio ni en el bundle web (test automático lo comprueba).
- **Ficheros**: URLs firmadas de corta duración; claves generadas por el servidor;
  validación de extensión, tipo, tamaño y **contenido real** (ffprobe) en Sprint 1.
- **Procesos**: FFmpeg/ffprobe con lista de argumentos, `-protocol_whitelist`,
  timeouts, directorio temporal aislado por trabajo y limpieza garantizada.
- **Auditoría**: tabla `audit_events` inmutable desde la aplicación (solo inserción).
- **Copias**: `infra/scripts/backup.sh` (pg_dump + réplica incremental del bucket);
  restauración documentada y probada.
- **Datos personales**: mínimos (usuarios internos; leads en V2). Grabaciones con
  personas: campo de consentimiento por activo desde Sprint 1.

## 10. Producción audiovisual (diseño objetivo, Sprints 1–4)

```mermaid
flowchart LR
  I[Importación MP4/MOV] --> O[(originals/)]
  O --> P[media.probe<br/>ffprobe + validación]
  P --> T[media.thumbnails<br/>miniaturas + proxy 540p]
  T --> S[media.segments<br/>escenas, silencios, negro,<br/>desenfoque, transcripción]
  S --> C[Clasificación<br/>manual + IA opcional]
  C --> M[Propuesta de montaje<br/>timeline v1]
  M --> E[Editor<br/>edición manual]
  E --> R[render.timeline<br/>FFmpeg]
  R --> V{Verificación<br/>ffprobe servidor}
  V -->|OK| X[(renders/ MP4)]
  V -->|KO| F[failed + motivo]
```

- La **línea de tiempo** es un documento JSON versionado (`timeline v1`, esquema en
  `docs/CONTRACTS.md §4`) con pistas, clips, posiciones, duraciones, recortes
  (*in/out*), reencuadre (rectángulo de recorte normalizado), textos, subtítulos y
  audio. Se guarda con historial de versiones y se puede volver a renderizar.
- **Render V1 con FFmpeg** (`filter_complex` generado desde la timeline): sin
  deformación (`scale` con `force_original_aspect_ratio` + `crop`/`pad`), subtítulos
  con libass dentro de zonas seguras 1080×1920, salida H.264 (High, yuv420p) + AAC
  48 kHz, 30 fps CFR, `+faststart`.
- **Remotion** queda como motor opcional para piezas gráficas. Su licencia exige
  *Company License* para empresas de más de 3 empleados; no se activará sin esa
  licencia (ver `docs/ENVIRONMENT_REVIEW.md §4`).
- **Música**: solo pistas de la biblioteca de marca con licencia registrada
  (campo `license_ref` obligatorio). Sin licencia, el render se hace sin música.

## 11. Director creativo IA (diseño objetivo, Sprint 2)

- Puerto `AIProvider` (implementación inicial: API de Anthropic, configurable por
  variable de entorno; el modelo es configuración, no código).
- **Base de conocimiento**: `knowledge_sources` (documento, URL o nota interna, con
  responsable y fecha de verificación) → `knowledge_facts` (afirmaciones atómicas
  aprobadas). La IA recibe solo hechos aprobados y debe citar sus IDs; la API
  rechaza/marca cualquier cifra o afirmación técnica sin cita.
- Cada pieza de contenido tiene: objetivo, público, plataforma, formato, duración,
  mensaje principal, CTA y estado de aprobación (`draft → in_review → approved |
  changes_requested`).
- Sin proveedor configurado: `GET /api/v1/system/status` devuelve
  `ai.configured = false`, la interfaz lo muestra de forma explícita y todos los
  formularios (guion, storyboard, calendario) funcionan en modo manual.

## 12. Observabilidad

- Logs JSON con `request_id`, `user_id`, `job_id`, `worker_id`.
- `GET /api/v1/health/live` y `/health/ready` (BD, Redis, storage).
- `GET /api/v1/system/status`: versiones, revisión de migración, workers en línea,
  proveedor IA configurado, ffprobe disponible.
- Eventos de trabajo consultables en la interfaz (Configuración → Trabajos).

## 13. Decisiones registradas

| ADR | Decisión |
|---|---|
| [0001](docs/adr/0001-postgres-job-queue.md) | Cola de trabajos en PostgreSQL + Redis como señal; protocolo HTTP de workers. |
| [0002](docs/adr/0002-server-side-sessions.md) | Sesiones de servidor con cookie opaca en vez de JWT. |
| [0003](docs/adr/0003-object-storage.md) | S3 genérico; SeaweedFS en desarrollo; MinIO descartado. |
| [0004](docs/adr/0004-ffmpeg-first-rendering.md) | FFmpeg como motor de render V1; Remotion opcional sujeto a licencia. |

## 14. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Ficheros MOV muy grandes (>5 GB) | Subida multiparte S3 (Sprint 1) y proxies 540p para edición. |
| Worker local apagado | Estado visible en dashboard; trabajos esperan en cola; lease + reintentos. |
| Alucinaciones de IA en datos técnicos | Solo hechos aprobados con cita obligatoria; revisión humana. |
| Licencias (Remotion, música) | Puertas de licencia explícitas; Remotion desactivado por defecto. |
| Pérdida de datos | Backups diarios de BD + réplica del bucket; prueba de restauración en Sprint 5. |
