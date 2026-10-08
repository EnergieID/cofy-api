# --- Build stage ---
FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# install git, to get git dependencies
RUN apk add --no-cache git

# `cofy-runner` depends on `cofy-api` through an editable local path, so both package sources
# are needed before `uv sync` can resolve it - there is no dependency-only layer to cache
# separately here.
COPY packages/api ./packages/api
COPY packages/runner ./packages/runner

RUN uv sync --project packages/runner --frozen --no-dev \
    && find /app/packages -path '*/.venv/*' -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- Final stage (no uv, no build deps) ---
FROM python:3.12-alpine

WORKDIR /app

# Copies the whole builder tree, not just the venv: `cofy-api` is installed editable, so the
# venv resolves it through a path back to packages/api/src at the same absolute location.
COPY --from=builder /app /app

ARG VERSION=dev
ENV APP_VERSION=${VERSION}

# The community configs are mounted in from the host, read-only; the image brings none of its own.
ENV COFY_RUNNER_DIRECTORY=/communities
VOLUME /communities

# uvicorn reads each of its options from a UVICORN_* variable, so a deployment overrides any of
# these the same way: UVICORN_PORT, or UVICORN_ROOT_PATH when a proxy serves the communities
# under a path prefix it strips, so their API docs point at where they really are.
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8080 \
    UVICORN_FORWARDED_ALLOW_IPS=*
CMD ["/app/packages/runner/.venv/bin/uvicorn", "cofy.runner.main:app"]
