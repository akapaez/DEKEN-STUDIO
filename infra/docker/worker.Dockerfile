# syntax=docker/dockerfile:1.7
# Worker de DEKEN STUDIO AI (render/análisis). Mismo contrato en local o en la nube.
#   docker build -f infra/docker/worker.Dockerfile -t deken/worker .
# Solo necesita DEKEN_API_URL y DEKEN_WORKER_TOKEN; no expone puertos.

FROM mwader/static-ffmpeg:7.1.1 AS ffmpeg

FROM python:3.12-slim AS build
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
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-render --no-install-workspace
COPY packages/shared/python packages/shared/python
COPY services/api/pyproject.toml services/api/
COPY workers/runtime workers/runtime
COPY workers/render workers/render
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --frozen --no-dev --package deken-render

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" \
    DEKEN_WORK_DIR=/work
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
RUN useradd --system --uid 10001 --home /app --shell /usr/sbin/nologin deken \
    && mkdir -p /work && chown deken /work
WORKDIR /app
COPY --from=build --chown=root:root /app /app
USER deken
VOLUME ["/work"]
CMD ["deken-worker", "run"]
