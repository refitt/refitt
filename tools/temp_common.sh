# shellcheck shell=sh
# Shared plumbing for tools/temp_db.sh and tools/temp_pg.sh. Sourced, never run.
#
# The caller sets `temp_name` (for messages) and `temp_kind` (for the state
# directory's name), sources this file, then calls, in order:
#
#   temp_preflight     refuse, before anything is created, to run where a
#                      throwaway run cannot be hermetic
#   temp_enter         create the state directory, make it HOME, TMPDIR and
#                      the working directory, redirect tool caches into it,
#                      and scrub inherited database, rootkey and libpq variables
#   temp_rootkey       export an API rootkey generated for this run
#   temp_run CMD...    run the command, recording its exit status in temp_status
#
# The EXIT trap stops whatever the helper started (the command's process group,
# a server's process group, a container), removes the state directory and exits
# with the status it was entered with. INT and TERM stop the command's whole
# process group first and exit 130 and 143. Every message goes to stderr.

temp_cmd=''
temp_server=''
temp_container=''
temp_state=''
temp_status=0

temp_say() { printf '%s: %s\n' "$temp_name" "$*" >&2; }
temp_die() { temp_say "$*"; exit 1; }

# The repository holding this helper, whatever directory it was called from.
REPO_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
temp_real_home=$HOME

# Run docker with the caller's HOME, so its contexts and credentials resolve
# after HOME moves into the state directory.
temp_docker() { HOME=$temp_real_home docker "$@"; }

temp_preflight() {
    # As root, REFITT keeps its state under /var/lib/refitt, outside any state directory.
    [ "$(id -u)" != 0 ] || temp_die "refusing to run as root: REFITT would write under /var/lib/refitt"
    # REFITT reads the system config file whatever HOME says, so its values would leak in.
    [ ! -e /etc/refitt.toml ] || temp_die "/etc/refitt.toml exists, and its values would leak into the throwaway run"
    temp_env=${UV_PROJECT_ENVIRONMENT:-.venv}
    case $temp_env in /*) ;; *) temp_env=$REPO_ROOT/$temp_env ;; esac
    # With UV_NO_SYNC and no environment, `uv run` would create an empty one in the worktree.
    [ -f "$temp_env/pyvenv.cfg" ] || temp_die "no environment at $temp_env; run 'uv sync --all-packages' first"
    command -v perl >/dev/null 2>&1 || temp_die "perl is required to run the command in its own process group"
}

# Signal a process group, wait for its leader, and KILL whatever is left. A
# watchdog sends KILL after 10 s if the leader ignores TERM.
temp_stop_group() {
    [ -n "$1" ] || return 0
    kill -TERM "-$1" 2>/dev/null || return 0
    ( sleep 10; kill -KILL "-$1" 2>/dev/null ) &
    temp_watchdog=$!
    wait "$1" 2>/dev/null || true
    kill -KILL "-$1" 2>/dev/null || true
    kill "$temp_watchdog" 2>/dev/null || true
    wait "$temp_watchdog" 2>/dev/null || true
}

temp_cleanup() {
    temp_rc=$?
    # A second INT or TERM must not cut the teardown short.
    trap '' INT TERM
    trap - EXIT
    set +e
    temp_stop_group "$temp_cmd"
    temp_stop_group "$temp_server"
    if [ -n "$temp_container" ]; then
        temp_docker rm -f -v "$temp_container" >/dev/null 2>&1 || true
    fi
    cd /
    if [ -n "$temp_state" ]; then
        # The command may leave read-only directories behind (pytest does, under TMPDIR).
        chmod -R u+w "$temp_state" 2>/dev/null
        rm -rf "$temp_state"
    fi
    exit "$temp_rc"
}

temp_signal() {
    trap '' INT TERM
    temp_stop_group "$temp_cmd"
    temp_cmd=''
    exit "$1"
}

trap temp_cleanup EXIT
trap 'temp_signal 130' INT
trap 'temp_signal 143' TERM

temp_enter() {
    # Keep uv's cache where the caller had it: HOME is about to move.
    if [ -z "${UV_CACHE_DIR:-}" ]; then
        UV_CACHE_DIR=$(uv cache dir 2>/dev/null) || UV_CACHE_DIR=''
    fi
    [ -z "$UV_CACHE_DIR" ] || export UV_CACHE_DIR
    # The environment the preflight checked, by absolute path: the cwd is about to move.
    [ -z "${UV_PROJECT_ENVIRONMENT:-}" ] || export UV_PROJECT_ENVIRONMENT="$temp_env"

    temp_state=$(mktemp -d "${TMPDIR:-/tmp}/refitt-temp-$temp_kind.XXXXXX")
    mkdir "$temp_state/tmp"

    # Inherited database and rootkey settings could point at real data or keys
    # (REFITT_API_ROOTKEY_EVAL would replace the key outright), and libpq's own
    # PG* variables override whatever host it is given (PGHOSTADDR).
    for temp_var in $(env | sed -n 's/^\(REFITT_DATABASE_[A-Za-z0-9_]*\)=.*/\1/p; s/^\(REFITT_API_ROOTKEY[A-Za-z0-9_]*\)=.*/\1/p; s/^\(PG[A-Z0-9_]*\)=.*/\1/p'); do
        unset "$temp_var"
    done

    # HOME and the working directory both in the state directory: REFITT's user
    # and local config paths point at files that never exist, and its
    # ~/.refitt/{lib,run,log} land here too.
    export REPO_ROOT
    export HOME="$temp_state"
    export TMPDIR="$temp_state/tmp"
    export UV_PROJECT="$REPO_ROOT"
    export UV_NO_SYNC=1
    export PYTHONPYCACHEPREFIX="$temp_state/pycache"
    export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:+$PYTEST_ADDOPTS }-o 'cache_dir=$temp_state/pytest-cache'"
    export REFITT_DATABASE_SCOPE_READ=default
    export REFITT_DATABASE_SCOPE_WRITE=default
    export REFITT_LOGGING_LEVEL="${REFITT_LOGGING_LEVEL:-warning}"
    cd "$temp_state"
}

# Call after the database variables are forced: the import reads configuration.
temp_rootkey() {
    REFITT_API_ROOTKEY=$(uv run python -c 'from refitt.api.token import Cipher; print(Cipher.new_rootkey().value)' </dev/null) \
        || temp_die "could not generate an API rootkey"
    export REFITT_API_ROOTKEY
}

# Runs its arguments as a new process group, so a signal reaches the whole tree.
temp_pgrp='$SIG{INT} = $SIG{QUIT} = "DEFAULT"; setpgrp(0, 0); exec { $ARGV[0] } @ARGV; print STDERR "$ARGV[0]: $!\n"; exit 127'

temp_run() {
    if [ -t 0 ]; then
        # A terminal: stay in the foreground, so the command can read it and
        # Ctrl-C reaches it directly.
        "$@" || temp_status=$?
    else
        # In the background, so INT and TERM are handled at once; fd 3 carries
        # the caller's stdin past the shell's /dev/null default for background jobs.
        exec 3<&0
        perl -e "$temp_pgrp" -- "$@" <&3 3<&- &
        temp_cmd=$!
        exec 3<&-
        wait "$temp_cmd" || temp_status=$?
        temp_cmd=''
    fi
}
