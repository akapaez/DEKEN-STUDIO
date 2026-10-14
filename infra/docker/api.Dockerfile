# syntax=docker/dockerfile:1.7
# API de DEKEN STUDIO AI. Contexto de build: raíz del repositorio.
#   docker build -f infra/docker/api.Dockerfile -t deken/api .
# Proxy corporativo con CA propia (opcional): --secret id=extra_ca,src=/ruta/ca.pem

FROM mwader/static-ffmpeg:7.1.1 AS ffmpeg

FROM python:3.12-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir "uv==0.11.*"
# Manifiestos primero (caché de dependencias), luego el código.
COPY pyproject.toml uv.lock ./
COPY packages/shared/python/pyproject.toml packages/shared/python/
COPY services/api/pyproject.toml services/api/
COPY workers/runtime/pyproject.toml workers/runtime/
COPY workers/render/pyproject.toml workers/render/
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-api --no-install-workspace
COPY packages/shared/python packages/shared/python
COPY services/api services/api
COPY workers/runtime workers/runtime
COPY workers/render workers/render
COPY infra/migrations infra/migrations
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-api

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe
RUN useradd --system --uid 10001 --home /app --shell /usr/sbin/nologin deken
WORKDIR /app
COPY --from=build --chown=root:root /app /app
COPY infra/docker/api-entrypoint.sh /usr/local/bin/api-entrypoint.sh
USER deken
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/usr/local/bin/api-entrypoint.sh"]
