# --- Frontend build stage ---
# `web-components` and the console resolve their `@cofy/*` dependencies through `file:` paths
# to the sibling packages' build output, so the three are installed and built in that order -
# matching `task build`.
FROM node:24-alpine AS frontend-builder
WORKDIR /app

COPY tsconfig.base.json ./
COPY packages/frontend-sdk/package.json packages/frontend-sdk/package-lock.json ./packages/frontend-sdk/
RUN cd packages/frontend-sdk && npm ci
COPY packages/frontend-sdk ./packages/frontend-sdk
RUN cd packages/frontend-sdk && npm run build

COPY packages/web-components/package.json packages/web-components/package-lock.json ./packages/web-components/
RUN cd packages/web-components && npm ci
COPY packages/web-components ./packages/web-components
RUN cd packages/web-components && npm run build

COPY apps/management-web/package.json apps/management-web/package-lock.json ./apps/management-web/
RUN cd apps/management-web && npm ci
COPY apps/management-web ./apps/management-web
RUN cd apps/management-web && npm run build

# --- API build stage ---
FROM python:3.12-alpine AS api-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# install git, to get git dependencies
RUN apk add --no-cache git

# `cofy-management-api` depends on `cofy-api` through an editable local path, so both package
# sources are needed before `uv sync` can resolve it - unlike the root Dockerfile's single
# package, there is no dependency-only layer to cache separately here.
COPY packages/api ./packages/api
COPY packages/management-api ./packages/management-api

RUN uv sync --project packages/management-api --frozen --no-dev \
    && find /app/packages/management-api/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- Final stage (no uv, no build deps, no node) ---
FROM python:3.12-alpine

WORKDIR /app

# Copies the whole builder tree, not just the venv: `cofy-api` is installed editable, so the
# venv resolves it through a path back to packages/api/src at the same absolute location.
COPY --from=api-builder /app /app
COPY --from=frontend-builder /app/apps/management-web/dist /app/console
COPY apps/demo_multitenant/seed /app/seed
COPY apps/demo_multitenant/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ARG VERSION=dev
ENV APP_VERSION=${VERSION}

# The console's own API client defaults to same-origin requests, so serving it from the same
# FastAPI app it talks to needs no CORS setup and no base URL to configure - see
# packages/management-api/src/cofy/management/main.py.
ENV COFY_MANAGEMENT_STATIC_DIR=/app/console

# Mount a volume here so community configs (and the modules they reference) survive a
# redeploy instead of resetting to the seed data every time.
ENV COFY_MANAGEMENT_DATA_DIR=/data
VOLUME /data

# Most cloud platforms inject a PORT env var - default to 8080 locally
ENTRYPOINT ["/app/docker-entrypoint.sh"]
