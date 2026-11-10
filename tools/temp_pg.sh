#!/bin/sh
# Run a command against a throwaway PostgreSQL REFITT database: the faithful
# tier for server, API and integration verify drives. It exercises the
# Postgres-only SQL that temp_db.sh's SQLite cannot (invariant §C4).
#
#   Usage:  tools/temp_pg.sh <command> [args...]
#           REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest "$REPO_ROOT/tests/test_web"'
#
# Bring-up. By default it starts an ephemeral `postgres:16` container
# (REFITT_TEST_PG_IMAGE overrides the image), published only on 127.0.0.1 at a
# port Docker picks, and runs nothing until a connection from the host
# succeeds. With no Docker daemon answering it stops before starting anything.
# To use an existing scratch database instead, export REFITT_TEST_PG=1 with
# REFITT_DATABASE_DEFAULT_{HOST,PORT,DATABASE,USER,PASSWORD}: its tables are
# dropped and recreated with `refitt database init --drop --test`. In container
# mode those variables are ignored, so a developer's own database is never
# reached.
#
# With REFITT_TEMP_WITH_SERVER=1 it also starts the dev API server on a free
# local port, exports REFITT_API_SITE and REFITT_API_PORT for it, and runs the
# command only once the server answers HTTP. Each bring-up wait is bounded
# (60 s for Postgres, 30 s for the server) and names what did not come up.
#
# Every Postgres session uses America/Indiana/Indianapolis, the zone the seed
# data assumes: PGTZ for libpq clients, and the container's server default.
#
# The command runs inside a fresh state directory, which is also its HOME and
# TMPDIR, so the developer's ~/.refitt and any repo-root .refitt config are
# never read or written; it finds the repository in $REPO_ROOT, so test paths
# are written "$REPO_ROOT/...". Pytest's cache and Python bytecode go to the
# state directory too. Inherited REFITT_DATABASE_* (but for the five above with
# REFITT_TEST_PG=1), REFITT_API_ROOTKEY* and libpq PG* variables are dropped,
# and the command gets a REFITT_API_ROOTKEY generated for this run, with or
# without the server. uv runs with UV_NO_SYNC against the existing
# environment, so it must already be synced, and uv.lock is never rewritten.
#
# The helper's own output goes to stderr, and it exits with the command's
# status. Without a terminal the command runs in its own process group; INT and
# TERM stop that group, and every exit path stops the server, removes the
# container and its volumes, and removes the state directory. It refuses to
# run as root, with /etc/refitt.toml present, or with no project environment,
# and needs perl.
set -eu

temp_name=temp_pg.sh
temp_kind=pg
. "$(dirname -- "$0")/temp_common.sh"

pg_zone=America/Indiana/Indianapolis
pg_wait=60
server_wait=30

if [ "${REFITT_TEST_PG:-0}" = 1 ]; then
    # Captured before temp_enter drops every inherited database variable.
    pg_host=${REFITT_DATABASE_DEFAULT_HOST:-127.0.0.1}
    pg_port=${REFITT_DATABASE_DEFAULT_PORT:-5432}
    pg_db=${REFITT_DATABASE_DEFAULT_DATABASE:-refitt_test}
    pg_user=${REFITT_DATABASE_DEFAULT_USER:-refitt}
    pg_password=${REFITT_DATABASE_DEFAULT_PASSWORD:-refitt}
else
    # Bounded: a wedged daemon, or one still starting, must not hang the helper.
    if ! command -v docker >/dev/null 2>&1 \
            || ! HOME=$temp_real_home perl -e 'alarm 10; exec { $ARGV[0] } @ARGV' -- docker info >/dev/null 2>&1; then
        temp_die "no Docker daemon answers; set REFITT_TEST_PG=1 with REFITT_DATABASE_DEFAULT_{HOST,PORT,DATABASE,USER,PASSWORD} to use a scratch Postgres instead"
    fi
    # Fixed throwaway credentials: nothing inherited reaches the container.
    pg_host=127.0.0.1
    pg_port=''
    pg_db=refitt_test
    pg_user=refitt
    pg_password=refitt
fi

temp_preflight
temp_enter
export PGTZ=$pg_zone

if [ "${REFITT_TEST_PG:-0}" != 1 ]; then
    temp_container="refitt-temp-pg-${temp_state##*.}"
    # TZ sets the server's default timezone at initdb, for sessions that skip PGTZ.
    temp_docker run -d --name "$temp_container" --label "refitt.temp-pg.state=$temp_state" \
        -e POSTGRES_DB="$pg_db" -e POSTGRES_USER="$pg_user" -e POSTGRES_PASSWORD="$pg_password" \
        -e TZ="$pg_zone" -p 127.0.0.1::5432 "${REFITT_TEST_PG_IMAGE:-postgres:16}" >/dev/null \
        || temp_die "could not start the Postgres container"
    pg_port=$(temp_docker port "$temp_container" 5432/tcp | sed -n 's/^127\.0\.0\.1:\([0-9][0-9]*\)$/\1/p' | head -n 1)
    [ -n "$pg_port" ] || temp_die "the Postgres container published no port on 127.0.0.1"
    # Wait for a real connection from the host: the image's first server only
    # listens on its socket, and Docker's proxy accepts TCP before Postgres does.
    pg_deadline=$(( $(date +%s) + pg_wait ))
    until PGHOST=$pg_host PGPORT=$pg_port PGDATABASE=$pg_db PGUSER=$pg_user PGPASSWORD=$pg_password PGCONNECT_TIMEOUT=2 \
            uv run python -c 'import psycopg2; psycopg2.connect("").close()' </dev/null >/dev/null 2>&1; do
        [ "$(temp_docker inspect -f '{{.State.Running}}' "$temp_container" 2>/dev/null)" = true ] \
            || temp_die "the Postgres container exited before accepting a connection"
        [ "$(date +%s)" -lt "$pg_deadline" ] \
            || temp_die "Postgres did not accept a connection from the host within ${pg_wait}s"
        sleep 1
    done
fi

export REFITT_DATABASE_DEFAULT_PROVIDER=postgresql
export REFITT_DATABASE_DEFAULT_HOST="$pg_host"
export REFITT_DATABASE_DEFAULT_PORT="$pg_port"
export REFITT_DATABASE_DEFAULT_DATABASE="$pg_db"
export REFITT_DATABASE_DEFAULT_USER="$pg_user"
export REFITT_DATABASE_DEFAULT_PASSWORD="$pg_password"

temp_rootkey

if [ -n "$temp_container" ]; then
    uv run refitt database init --drop --test </dev/null >&2 \
        || temp_die "could not create and seed the throwaway database"
else
    # A scratch database on a remote host still asks before dropping it.
    uv run refitt database init --drop --test >&2 \
        || temp_die "could not create and seed the scratch database"
fi

if [ "${REFITT_TEMP_WITH_SERVER:-0}" = 1 ]; then
    api_port=$(uv run python -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()' </dev/null) \
        || temp_die "could not pick a port for the dev server"
    export REFITT_API_SITE=http://localhost
    export REFITT_API_PORT="$api_port"
    # Its own process group: the werkzeug reloader forks a child that a
    # single-pid kill would orphan.
    perl -e "$temp_pgrp" -- uv run refitt-server start --dev --port "$api_port" </dev/null >&2 &
    temp_server=$!
    server_deadline=$(( $(date +%s) + server_wait ))
    until uv run python -c '
import sys, urllib.error, urllib.request
# No proxy: an error page from a proxy would read as the server answering.
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    opener.open(sys.argv[1], timeout=2)
except urllib.error.HTTPError:
    pass
' "http://127.0.0.1:$api_port/" </dev/null >/dev/null 2>&1; do
        [ "$(date +%s)" -lt "$server_deadline" ] \
            || temp_die "the dev server did not answer HTTP within ${server_wait}s"
        sleep 1
    done
fi

temp_run "$@"
exit "$temp_status"
