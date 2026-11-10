#!/bin/sh
# Run a command against a throwaway SQLite REFITT database: the fast tier for
# factory verify drives.
#
#   Usage:  tools/temp_db.sh <command> [args...]
#           tools/temp_db.sh sh -c 'uv run pytest -m unit "$REPO_ROOT/tests/test_database"'
#
# The command runs inside a fresh state directory, which is also its HOME and
# TMPDIR, so the developer's ~/.refitt and any repo-root .refitt config are
# never read or written; it finds the repository in $REPO_ROOT, so test paths
# are written "$REPO_ROOT/...". Pytest's cache and Python bytecode go to the
# state directory too. Inherited REFITT_DATABASE_*, REFITT_API_ROOTKEY* and
# libpq PG* variables are dropped, and the command gets a REFITT_API_ROOTKEY
# generated for this run. uv runs with UV_NO_SYNC against the existing
# environment, so it must already be synced, and uv.lock is never rewritten.
#
# The database is created and seeded with `refitt database init --test`
# (override the flags with REFITT_TEMP_DB_INIT, e.g. "--core") before the
# command runs. `init` asks for confirmation on every SQLite database
# (issues/init-sqlite-prompt.md); the helper answers it itself, so nothing
# waits on a terminal, and the prompt line goes to stderr with the rest of
# init's output.
#
# The helper's own output goes to stderr, and it exits with the command's
# status. Without a terminal the command runs in its own process group; INT and
# TERM stop that group, and every exit path removes the state directory.
# It refuses to run as root, with /etc/refitt.toml present, or with no project
# environment, and needs perl.
#
# SQLite does not exercise Postgres-only SQL (invariant §C4): use temp_pg.sh
# for server, API and integration drives.
set -eu

temp_name=temp_db.sh
temp_kind=db
. "$(dirname -- "$0")/temp_common.sh"

temp_preflight
temp_enter

export REFITT_DATABASE_DEFAULT_PROVIDER=sqlite
export REFITT_DATABASE_DEFAULT_FILE="$temp_state/refitt.db"

temp_rootkey

# `init` prompts on every SQLite database; answer it so nothing waits on a terminal.
# shellcheck disable=SC2086
printf 'y\n' | uv run refitt database init ${REFITT_TEMP_DB_INIT:---test} >&2 \
    || temp_die "could not create and seed the throwaway database"
# The prompt line ends without a newline.
printf '\n' >&2

temp_run "$@"
exit "$temp_status"
