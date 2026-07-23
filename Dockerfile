# syntax=docker/dockerfile:1
# REFITT container image — uv-based, multi-stage. Unlike a wheels-only project, REFITT has
# native deps (psycopg2->libpq, confluent-kafka->librdkafka), so the build toolchain and -dev
# headers live ONLY in the builder stage; the runtime stage ships just the runtime shared libs.
# Kept in sync with ./Apptainer. The version is single-sourced from pyproject.toml and stamped
# onto the image by CI (docker/metadata-action) — no static version label here.

# ------------------------------------------------------------------------------------------
# Builder: resolve + install the whole workspace into a self-contained venv at /opt/refitt.
# ------------------------------------------------------------------------------------------
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build-time system deps for the native sdists (psycopg2, confluent-kafka).
RUN --mount=type=cache,target=/var/cache/apt \
    DEBIAN_FRONTEND=noninteractive apt-get -yqq update && \
    apt-get -yqq install --no-install-recommends \
        build-essential libpq-dev librdkafka-dev && \
    rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/refitt \
    UV_PYTHON_PREFERENCE=only-system

WORKDIR /app
COPY . .
# --no-editable copies each workspace member's code into the venv, so the runtime stage needs
# only /opt/refitt (not the /app source tree). --python 3.13 pins the base image's interpreter
# so the copied venv resolves against a python that also exists in the runtime stage.
# NOTE: switch to `uv sync --frozen` once the workspace lockfile is regenerated on a
# librdkafka-enabled env (release-prep follow-up).
RUN uv sync --all-packages --no-editable --python 3.13

# ------------------------------------------------------------------------------------------
# Runtime: slim image with only the runtime shared libs + the prebuilt venv.
# ------------------------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="REFITT"
LABEL org.opencontainers.image.description="Recommender Engine for Intelligent Transient Tracking"
LABEL org.opencontainers.image.source="https://github.com/refitt/refitt"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.authors="glentner@purdue.edu"

# Runtime shared libraries only: libpq5 for psycopg2, librdkafka1 for confluent-kafka.
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq update && \
    apt-get -yqq install --no-install-recommends libpq5 librdkafka1 && \
    rm -rf /var/lib/apt/lists/*

# Non-root runtime user with a writable HOME (REFITT resolves config/lib/log under ~/.refitt).
RUN groupadd --gid 1001 --system refitt && \
    useradd --uid 1001 --gid 1001 --system --home-dir /var/lib/refitt --create-home refitt && \
    mkdir -p /var/lib/refitt /var/log/refitt /var/run/refitt && \
    chown -R refitt:refitt /var/lib/refitt /var/log/refitt /var/run/refitt

COPY --from=builder --chown=refitt:refitt /opt/refitt /opt/refitt

ENV PATH=/opt/refitt/bin:$PATH \
    HOME=/var/lib/refitt \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    REFITT_LOGGING_LEVEL=INFO

USER refitt
WORKDIR /var/lib/refitt

# Default to the API server; override with any console entry point, e.g.
#   docker run --rm <image> refitt-broker ...
#   docker run --rm <image> refitt --help
CMD ["refitt-server", "start"]
