# syntax=docker/dockerfile:1.7
# Worker de DEKEN STUDIO AI: análisis/ingesta (FFmpeg) y render (FFmpeg + motor Remotion).
# Mismo contrato en local o en la nube.
#   docker build -f infra/docker/worker.Dockerfile -t deken/worker .
# Solo necesita DEKEN_API_URL y DEKEN_WORKER_TOKEN; no expone puertos.
# Licencia de Remotion (ADR 0005): por defecto DEKEN_REMOTION_LICENSE_MODE=evaluation
# (solo renders de evaluación con marca de agua). La clave de empresa, si existe, se
# inyecta en ejecución (DEKEN_REMOTION_LICENSE_KEY), nunca en la imagen.
# Comprobación del motor dentro de la imagen:  docker run --rm deken/worker deken-remotion-check

FROM mwader/static-ffmpeg:7.1.1 AS ffmpeg
FROM node:22.22.0-bookworm-slim AS node

# --- Motor Remotion: renderer, bundle de composiciones y Chrome Headless Shell -------------
FROM node AS remotion
ENV PNPM_HOME=/pnpm PATH="/pnpm:$PATH"
WORKDIR /repo
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    corepack enable && corepack prepare pnpm@10.28.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/brand/package.json packages/brand/
COPY packages/video-compositions/package.json packages/video-compositions/
COPY workers/render/remotion/package.json workers/render/remotion/
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    pnpm install --frozen-lockfile --filter "@deken/remotion-renderer..."
COPY packages/brand packages/brand
COPY packages/video-compositions packages/video-compositions
COPY workers/render/remotion workers/render/remotion
RUN pnpm --filter @deken/remotion-renderer build \
    && cd workers/render/remotion && node dist/bundle.js dist/bundle
# Árbol de producción autocontenido (sin dependencias de desarrollo).
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    pnpm --filter @deken/remotion-renderer deploy --prod --legacy /out \
    && rm -rf /out/dist && cp -r workers/render/remotion/dist /out/dist
# Chrome Headless Shell de la versión que fija @remotion/renderer, en una ruta estable.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    cd /out && node -e "import('@remotion/renderer').then((r) => r.ensureBrowser())" \
    && bin="$(find /out/node_modules/.remotion -type f -name chrome-headless-shell | head -n 1)" \
    && test -n "$bin" \
    && mkdir -p /out/chrome && cp -a "$(dirname "$bin")/." /out/chrome/ \
    && rm -rf /out/node_modules/.remotion

# --- Python: runtime del worker + handlers de render y análisis ---------------------------
FROM python:3.12-slim-bookworm AS build
ENV PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir "uv==0.11.*"
COPY pyproject.toml uv.lock ./
COPY packages/shared/python/pyproject.toml packages/shared/python/
COPY services/api/pyproject.toml services/api/
COPY workers/runtime/pyproject.toml workers/runtime/
COPY workers/render/pyproject.toml workers/render/
COPY workers/analysis/pyproject.toml workers/analysis/
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-render --package deken-analysis \
      --no-install-workspace
COPY packages/shared/python packages/shared/python
COPY workers/runtime workers/runtime
COPY workers/render/pyproject.toml workers/render/
COPY workers/render/src workers/render/src
COPY workers/analysis workers/analysis
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-render --package deken-analysis

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" \
    DEKEN_WORK_DIR=/work \
    DEKEN_NODE_PATH=/usr/local/bin/node \
    DEKEN_REMOTION_RENDERER=/opt/remotion/dist/cli.js \
    DEKEN_REMOTION_BUNDLE_DIR=/opt/remotion/dist/bundle \
    DEKEN_REMOTION_BROWSER=/opt/remotion/chrome/chrome-headless-shell \
    DEKEN_REMOTION_LICENSE_MODE=evaluation
# Bibliotecas que necesita Chrome Headless Shell (las tipografías de marca van en el bundle).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libexpat1 \
      libglib2.0-0 libx11-6 libxcb1 libxext6 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libxkbcommon0 libgbm1 libudev1 libasound2 libpango-1.0-0 libcairo2 libcups2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN useradd --system --uid 10001 --home /app --shell /usr/sbin/nologin deken \
    && mkdir -p /work && chown deken /work
WORKDIR /app
COPY --from=build --chown=root:root /app /app
COPY --from=remotion --chown=root:root /out /opt/remotion
USER deken
VOLUME ["/work"]
CMD ["deken-worker", "run"]
