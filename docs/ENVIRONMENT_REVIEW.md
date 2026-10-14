# Revisión técnica del entorno y de licencias

Fecha de la revisión: 2026-10-14.

## 1. Entorno de desarrollo inspeccionado

Contenedor de desarrollo en la nube (Ubuntu 24.04.5 LTS, 4 vCPU, 15 GiB RAM, sin GPU).
El repositorio estaba **vacío** (sin commits): no hay código previo que migrar.

| Herramienta | Versión encontrada | Uso |
|---|---|---|
| Node.js | 22.22.0 | `apps/web`, herramientas TS |
| pnpm | 10.28.0 | Workspace JS |
| Python | 3.13.16 | API y workers (objetivo `>=3.12`) |
| uv | 0.11.32 | Workspace Python, lockfile |
| FFmpeg / ffprobe | 6.1.1 (Ubuntu) — `libx264`, `aac`, `libass`, `drawtext`, `scale/crop/pad` | Render y análisis |
| PostgreSQL | 16.15 (binarios cliente y servidor) | BD (tests locales sin Docker) |
| Redis | 7.0.15 | Señales de cola y rate-limit |
| Docker / Compose | 29.8.2 / v5.6.0 | Servicios de infraestructura |
| Chromium (Playwright) | revisión 1194 (= Playwright 1.56.x) | Tests E2E |

### Restricciones encontradas en este entorno

- **Docker Hub** devuelve `429 Too Many Requests`; las imágenes se obtienen a través
  del espejo `mirror.gcr.io` (mismo contenido que Docker Hub). En el equipo de DEKEN
  no aplica.
- Los repositorios **apt/apk** (deb.debian.org, dl-cdn.alpinelinux.org) están
  bloqueados por la política de red del entorno. Por eso las imágenes Docker copian
  FFmpeg desde la imagen estática `mwader/static-ffmpeg:7.1.1` en lugar de
  instalarlo con `apt`. Esto además fija la versión de FFmpeg de forma reproducible.
- `dl.min.io` bloqueado (irrelevante: MinIO se descarta por licencia, ver §4).

### Entorno objetivo del worker local

Windows 10/11 con **WSL2 (Ubuntu 24.04)**. Requisitos: FFmpeg ≥ 6.1 con libx264 y
libass, Python ≥ 3.12, `uv`. Opcional: GPU NVIDIA con `h264_nvenc` (el worker
detecta y declara sus codificadores como *capabilities*). Conexión **solo saliente**
HTTPS hacia la API. Guía: [deployment/WORKER_WSL2.md](deployment/WORKER_WSL2.md).

## 2. Versiones fijadas

| Paquete | Versión | Nota |
|---|---|---|
| next | 16.3.x | Última serie de parches con más de dos semanas de antigüedad |
| react / react-dom | 19.x | |
| typescript | 5.9.3 | Se evita TS 7 (port nativo) hasta que Next declare compatibilidad con su API programática |
| @playwright/test | 1.56.1 | Coincide con el Chromium preinstalado |
| fastapi | 0.14x | |
| sqlalchemy | 2.x (async) + asyncpg | |
| alembic | 1.x | |
| pydantic | 2.x | |
| FFmpeg (imágenes Docker) | 7.1.1 estático (`mwader/static-ffmpeg`) | El host de desarrollo usa 6.1.1; ambos verificados |
| PostgreSQL | 16 | |
| Valkey (protocolo Redis) | 8 | Licencia BSD-3 |
| SeaweedFS | imagen `chrislusf/seaweedfs` (fijar digest en producción) | |

Las versiones exactas quedan en `uv.lock` y `pnpm-lock.yaml`.

## 3. Compatibilidad

- Python 3.12 (imagen Docker) y 3.13 (host) — se prueba con ambas en CI.
- Next 16 renombra `middleware.ts` a `proxy.ts`; se usa la convención nueva.
- WSL2: FFmpeg de Ubuntu 24.04 (6.1.1) cumple los requisitos (libx264, aac, libass).
- Sin GPU en desarrollo: todo el pipeline funciona en CPU; NVENC es una optimización
  declarada por capabilities, nunca un requisito.

## 4. Licencias

| Componente | Licencia | Valoración |
|---|---|---|
| Next.js, React, TanStack Query, openapi-fetch, openapi-typescript, zod, lucide-react | MIT / ISC | ✅ Sin restricciones |
| FastAPI, Pydantic, SQLAlchemy, Alembic, argon2-cffi, structlog, redis-py, httpx | MIT / BSD | ✅ |
| boto3, asyncpg, moto (solo tests) | Apache-2.0 | ✅ |
| PostgreSQL | PostgreSQL License | ✅ |
| Redis 7.0–7.2 | BSD-3 | ✅ (Redis ≥ 7.4 cambió a RSALv2/SSPL; desde 8.0 también AGPLv3). Para uso interno no distribuido no hay problema con ninguna, pero se usa **Valkey 8** (BSD-3, compatible con el protocolo) en Docker Compose. |
| SeaweedFS | Apache-2.0 | ✅ Elegido para S3 local |
| MinIO | AGPL-3.0; la edición comunitaria dejó de distribuir binarios/imágenes oficiales en 2025 | ❌ Descartado: mantenimiento incierto |
| FFmpeg (builds con libx264) | GPL-2.0+ | ✅ Uso interno como proceso externo (no se enlaza ni se distribuye). Si algún día se distribuye el worker a terceros, revisar obligaciones GPL. |
| Montserrat, IBM Plex Mono | SIL OFL-1.1 | ✅ Se sirven localmente |
| faster-whisper / modelos Whisper | MIT | ✅ (Sprint 3) |
| **Remotion** | Licencia propia: gratis para particulares y empresas **≤ 3 empleados**; *Company License* de pago para el resto | ⚠️ Grupo Deken necesita **Company License** para usar Remotion en esta plataforma. V1 no depende de Remotion; el motor queda desactivado hasta que DEKEN confirme la licencia. Las animaciones que ya se hacen con Remotion fuera de la plataforma están igualmente sujetas a esta licencia. |
| Música | Según biblioteca | ⚠️ Solo pistas con licencia registrada (`license_ref`). |
| APIs de IA | Términos del proveedor | ⚠️ Revisar tratamiento de datos (no enviar datos personales; RGPD). |

## 5. Activos de marca reales identificados

La skill de marca de DEKEN (`estilo-de-marca`) documenta valores medidos sobre los
logos reales, que `packages/brand` adopta tal cual:

- Verde Deken `#76B82A` (único acento) y Gris Deken `#383E42`.
- Neutros derivados del gris (tono 204°, saturación 8,2 %).
- **Texto blanco sobre verde prohibido** (2,42:1); sobre verde se usa `#0D0E0F`.
- Montserrat para marca; IBM Plex Mono para interfaz técnica, código y etiquetas.
- Logos oficiales en `Deken-Recursos/Versiones-Logo/` (no incluidos en este
  repositorio). Hay dos ficheros con nombre cambiado (horizontal blanco/gris): la
  plataforma calcula el color dominante al subirlos (Sprint 1) en vez de fiarse del
  nombre.

No se incluye ningún logo en el repositorio: la interfaz muestra el nombre del
producto en texto hasta que un administrador suba los logos oficiales (Sprint 1).
