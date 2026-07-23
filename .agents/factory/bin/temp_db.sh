#!/bin/sh
# Run a command against a throwaway, hermetic SQLite REFITT database so factory
# verify/review drives never touch the developer's real database, logs, or config.
#
#   Usage:  .agents/factory/bin/temp_db.sh <command> [args...]
#           .agents/factory/bin/temp_db.sh sh -c "uv run pytest -m unit tests/test_database"
#
# FAST TIER (SQLite). The database is created and seeded with the test dataset
# (`refitt database init --test`) before the command runs, then discarded.
#
# NOTE: Postgres-only SQL (e.g. `Object.from_alias` uses the raw `->>` operator)
# and schema-qualified paths are NOT exercised here — use temp_pg.sh for
# server/API/integration phases (invariant §C4).
#
# CAVEAT (first cut, to be hardened by the test-suite-rehab feature): env has the
# highest config precedence, so provider/file/scope are forced below; but a user
# config that adds host/user to `database.default` could still interfere. Run on a
# machine without a conflicting ~/.refitt database config, or set REFITT_TEST_PG=1
# and use temp_pg.sh.
set -eu

root="$(pwd)"
site="$(mktemp -d "${TMPDIR:-/tmp}/refitt-temp-db.XXXXXX")"
trap 'rm -rf "$site"' EXIT INT TERM

# Pin uv project discovery back to the repo (cwd becomes the throwaway site, which
# has no pyproject.toml; uv would otherwise walk up from /tmp and find nothing).
export UV_PROJECT="$root"

# Force a throwaway SQLite database via env (highest config precedence).
export REFITT_DATABASE_SCOPE_READ=default
export REFITT_DATABASE_SCOPE_WRITE=default
export REFITT_DATABASE_DEFAULT_PROVIDER=sqlite
export REFITT_DATABASE_DEFAULT_FILE="$site/refitt.db"
export REFITT_LOGGING_LEVEL="${REFITT_LOGGING_LEVEL:-warning}"

# Contain any relative writes/logs inside the throwaway site.
cd "$site"

# Create + seed the schema (test seed by default; override with REFITT_TEMP_DB_INIT,
# e.g. "--core" or "--drop --test").
# shellcheck disable=SC2086
uv run refitt database init ${REFITT_TEMP_DB_INIT:---test}

# Run the caller's command with the throwaway DB active; preserve its exit code so
# the trap can still clean up (do not `exec`).
status=0
"$@" || status=$?
exit "$status"
