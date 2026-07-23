#!/bin/sh
# Run a command against a throwaway, hermetic PostgreSQL REFITT database — the
# FAITHFUL TIER for server/API/integration verify drives. Exercises Postgres-only
# SQL that temp_db.sh's SQLite cannot (invariant §C4).
#
#   Usage:  .agents/factory/bin/temp_pg.sh <command> [args...]
#           REFITT_TEMP_WITH_SERVER=1 .agents/factory/bin/temp_pg.sh sh -c "uv run pytest tests/test_web"
#
# BRING-UP: by default starts an ephemeral `postgres` docker container and tears it
# down on exit. To reuse an existing Postgres instead, export REFITT_TEST_PG=1 with
# REFITT_DATABASE_DEFAULT_{HOST,PORT,DATABASE,USER,PASSWORD} pointing at a SCRATCH
# database (it is dropped and recreated).
#
# CAVEAT (first cut, to be hardened by the test-suite-rehab feature): the optional
# API-server path (REFITT_TEMP_WITH_SERVER=1) and the docker lifecycle are minimal.
set -eu

root="$(pwd)"
export UV_PROJECT="$root"

PG_IMAGE="${REFITT_TEST_PG_IMAGE:-postgres:16}"
PG_DB="${REFITT_DATABASE_DEFAULT_DATABASE:-refitt_test}"
PG_USER="${REFITT_DATABASE_DEFAULT_USER:-refitt}"
PG_PASSWORD="${REFITT_DATABASE_DEFAULT_PASSWORD:-refitt}"
PG_HOST="${REFITT_DATABASE_DEFAULT_HOST:-127.0.0.1}"
PG_PORT="${REFITT_DATABASE_DEFAULT_PORT:-5544}"

container=""
server_pid=""
cleanup() {
    status=$?
    [ -n "$server_pid" ] && kill "$server_pid" 2>/dev/null || true
    [ -n "$container" ] && docker rm -f "$container" >/dev/null 2>&1 || true
    exit "$status"
}
trap cleanup EXIT INT TERM

if [ "${REFITT_TEST_PG:-0}" != "1" ]; then
    command -v docker >/dev/null 2>&1 || {
        echo "temp_pg.sh: docker not found; set REFITT_TEST_PG=1 to reuse an external Postgres" >&2
        exit 127
    }
    container="refitt-temp-pg-$$"
    docker run -d --name "$container" \
        -e POSTGRES_DB="$PG_DB" -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" \
        -p "$PG_PORT:5432" "$PG_IMAGE" >/dev/null
    tries=0
    until docker exec "$container" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
        tries=$((tries + 1))
        [ "$tries" -gt 60 ] && { echo "temp_pg.sh: Postgres did not become ready in 60s" >&2; exit 1; }
        sleep 1
    done
fi

export REFITT_DATABASE_SCOPE_READ=default
export REFITT_DATABASE_SCOPE_WRITE=default
export REFITT_DATABASE_DEFAULT_PROVIDER=postgresql
export REFITT_DATABASE_DEFAULT_DATABASE="$PG_DB"
export REFITT_DATABASE_DEFAULT_USER="$PG_USER"
export REFITT_DATABASE_DEFAULT_PASSWORD="$PG_PASSWORD"
export REFITT_DATABASE_DEFAULT_HOST="$PG_HOST"
export REFITT_DATABASE_DEFAULT_PORT="$PG_PORT"
export REFITT_LOGGING_LEVEL="${REFITT_LOGGING_LEVEL:-warning}"

# Recreate + seed the schema.
uv run refitt database init --drop --test

# Optionally launch the API server for endpoint drives.
if [ "${REFITT_TEMP_WITH_SERVER:-0}" = "1" ]; then
    export REFITT_API_ROOTKEY="${REFITT_API_ROOTKEY:-$(uv run python -c 'from refitt.api.token import Cipher; print(Cipher.new_rootkey().value)')}"
    export REFITT_API_SITE="${REFITT_API_SITE:-http://localhost}"
    export REFITT_API_PORT="${REFITT_API_PORT:-5050}"
    uv run refitt-server start --dev --port "$REFITT_API_PORT" &
    server_pid=$!
    sleep 5
fi

status=0
"$@" || status=$?
exit "$status"
