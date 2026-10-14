# syntax=docker/dockerfile:1.7
# Web de DEKEN STUDIO AI (Next.js standalone).
#   docker build -f infra/docker/web.Dockerfile -t deken/web .
# En ejecución: DEKEN_API_INTERNAL_URL (URL de la API) y DEKEN_MEDIA_ORIGINS (CSP de medios).

FROM node:22-alpine AS build
ENV NEXT_TELEMETRY_DISABLED=1 PNPM_HOME=/pnpm PATH="/pnpm:$PATH"
WORKDIR /repo
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    corepack enable && corepack prepare pnpm@10.28.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/web/package.json apps/web/
COPY packages/brand/package.json packages/brand/
COPY packages/shared/ts/package.json packages/shared/ts/
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    pnpm install --frozen-lockfile --filter "@deken/web..."
COPY packages/brand packages/brand
COPY packages/shared/ts packages/shared/ts
COPY apps/web apps/web
RUN pnpm --filter @deken/web build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S deken && adduser -S -G deken -u 10001 deken
COPY --from=build --chown=deken:deken /repo/apps/web/.next/standalone ./
COPY --from=build --chown=deken:deken /repo/apps/web/.next/static ./apps/web/.next/static
USER deken
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
