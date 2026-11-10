# shellcheck shell=sh
# Shared setup for the verify-helpers-harden gates. Sourced, never run.
#
# Footprint: one helper run at a time (the container drive runs two at once,
# once), each a POSIX shell, a perl process-group wrapper, uv, and one Python
# (~150 MB); the first run on a host also builds the gate environment
# (uv sync, ~1 GB of wheels into the uv cache). No other parallel work.
#
# Every lab lives under ${TMPDIR:-/tmp} and is left for the OS: the gates never
# delete anything.
#
# The gate environment. The committed uv.lock is stale (it lacks the refitt-host
# member), so `uv sync --frozen` refuses it, and an unfrozen sync in the cycle
# worktree would rewrite it. The environment is therefore built once per host
# in a cache directory, from its own copy of the tree: there an unfrozen sync
# may re-lock freely. numpy is pinned back to the committed lock's version
# (the re-lock picks a numpy that astropy 7.0.1 cannot import), psycopg2 comes
# from the psycopg2-binary wheel (no libpq needed), and confluent-kafka is not
# installed (no librdkafka needed; only refitt-broker imports it). The helpers
# reach it through UV_PROJECT_ENVIRONMENT; nothing under py/ changes in this
# cycle, so its editable installs run the same product code as the fixture.

vhh_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
vhh_wt=$(git -C "$vhh_dir" rev-parse --show-toplevel)
vhh_slug=verify-helpers-harden

vhh_ok() { printf 'ok %s\n' "$*"; }
vhh_fail() { printf 'FAIL %s\n' "$*"; exit 1; }
vhh_note() { printf '.. %s\n' "$*"; }

vhh_lab() {
    vhh_lab=$(mktemp -d "${TMPDIR:-/tmp}/vhh-gate.XXXXXX")
    vhh_runs=0
    vhh_note "lab $vhh_lab"
}

# Export a tree into $2: `index` (what the phase staged) or `head` (committed).
vhh_fixture() {
    mkdir -p "$2"
    case $1 in
        index) git -C "$vhh_wt" checkout-index -a --prefix="$2/" ;;
        head) git -C "$vhh_wt" archive HEAD | tar -x -C "$2" ;;
        *) vhh_fail "fixture: unknown source $1" ;;
    esac
}

vhh_env() {
    vhh_key=$(git -C "$vhh_wt" ls-files -s -- py pyproject.toml uv.lock src | git hash-object --stdin | cut -c1-12)
    vhh_envdir=${VHH_ENV_DIR:-${TMPDIR:-/tmp}/vhh-env-$vhh_key}
    vhh_py="$vhh_envdir/venv/bin/python"
    # Rebuild when missing or damaged (a helper that syncs would re-lock and upgrade it).
    if ! vhh_env_sound; then
        vhh_note "building the gate environment in $vhh_envdir"
        mkdir -p "$vhh_envdir/src"
        git -C "$vhh_wt" checkout-index -a -f --prefix="$vhh_envdir/src/"
        ( cd "$vhh_envdir/src" \
          && UV_PROJECT_ENVIRONMENT="$vhh_envdir/venv" uv sync --all-packages \
                --python "${VHH_PYTHON:-3.13}" --no-install-package psycopg2 \
                --no-install-package confluent-kafka >&2 ) \
            || vhh_fail "env: uv sync in $vhh_envdir/src"
        # shellcheck disable=SC2046
        uv pip install --python "$vhh_py" $(vhh_env_pins) >&2 || vhh_fail "env: pinning numpy and psycopg2-binary"
        vhh_env_sound || vhh_fail "env: still unsound after a rebuild"
    fi
    export UV_PROJECT_ENVIRONMENT="$vhh_envdir/venv"
    # Resolve uv's cache while HOME is still real: helper runs point HOME at
    # the populated developer home, which must stay untouched.
    UV_CACHE_DIR=${UV_CACHE_DIR:-$(uv cache dir)}
    export UV_CACHE_DIR
}

# numpy and psycopg2 at the committed lock's versions (psycopg2 as its binary wheel).
vhh_env_pins() {
    "$vhh_py" -I -c '
import sys, tomllib
lock = tomllib.load(open(sys.argv[1], "rb"))
pins = {p["name"]: p["version"] for p in lock["package"] if "version" in p}
print("numpy==" + pins["numpy"], "psycopg2-binary==" + pins["psycopg2"])
' "$vhh_wt/uv.lock"
}

# Checked by metadata only: importing refitt would write under the real HOME.
vhh_env_sound() {
    [ -x "$vhh_py" ] || return 1
    "$vhh_py" -I -c '
import sys
from importlib.metadata import version
want = dict(p.split("==") for p in sys.argv[1:])
for dist in ("refitt-admin", "refitt-server", "refitt-api", "pytest", "flask"):
    version(dist)
assert all(version(d) == v for d, v in want.items()), "pins drifted"
' $(vhh_env_pins 2>/dev/null) >/dev/null 2>&1
}

vhh_manifest() { "$vhh_py" -I "$vhh_dir/tree_manifest.py" "$1"; }

# A developer home and a repo-root local config, both holding values the
# throwaway run must never see (GOAL: "a populated home").
vhh_populate() {
    mkdir -p "$1/.refitt" "$2/.refitt"
    cat > "$1/.refitt/config.toml" <<'EOF'
[database.default]
provider = "postgresql"
database = "dev_real"
host = "db.dev.invalid"
user = "dev_user"
password = "dev_password"
port = 6543

[api]
rootkey_eval = "echo dev-rootkey-from-eval"
EOF
    cat > "$2/.refitt/config.toml" <<'EOF'
[database.default]
database = "local_real"

[console]
theme = "local-marker"
EOF
    chmod 600 "$1/.refitt/config.toml" "$2/.refitt/config.toml"
}

# Run ARGS with INT at its default disposition (a background job of a script
# starts with INT ignored, and a shell cannot trap a signal ignored on entry).
# After VHH_BUDGET seconds (default 300) it sends TERM, so the helper's own
# teardown runs, then KILL 30 s later; the exit status is the child's.
vhh_timed() {
    perl -e '
my $budget = shift;
my $pid = fork;
die "fork: $!" unless defined $pid;
if (!$pid) { $SIG{INT} = "DEFAULT"; exec { $ARGV[0] } @ARGV; exit 127 }
local $SIG{ALRM} = sub { kill "TERM", $pid; sleep 30; kill "KILL", $pid };
alarm $budget;
waitpid $pid, 0;
exit($? & 127 ? 128 + ($? & 127) : $? >> 8);
' "${VHH_BUDGET:-300}" "$@"
}

# vhh_run NAME HELPER ARGS...: run a helper from the fixture root with stdin
# from /dev/null, its own empty TMPDIR, the populated home, inherited database,
# rootkey and libpq variables, under vhh_timed. Leaves $vhh_out/NAME.{out,err,rc}
# and sets vhh_rc and vhh_tmp.
vhh_run() {
    vhh_name=$1; shift
    vhh_tmp="$vhh_lab/tmp-$vhh_name"
    mkdir -p "$vhh_tmp"
    ( cd "$vhh_fixture_dir" && \
      HOME="$vhh_home" TMPDIR="$vhh_tmp" VHH_OUT="$vhh_out" VHH_DIR="$vhh_dir" \
      REFITT_DATABASE_DEFAULT_HOST=db.inherited.invalid \
      REFITT_DATABASE_DEFAULT_PORT=1 \
      REFITT_DATABASE_DEFAULT_DATABASE=inherited_real \
      REFITT_DATABASE_DEFAULT_USER=inherited_user \
      REFITT_DATABASE_DEFAULT_PASSWORD=inherited_password \
      REFITT_DATABASE_DEFAULT_SCHEMA=inherited_schema \
      REFITT_API_ROOTKEY=inherited-rootkey \
      REFITT_API_ROOTKEY_EVAL='echo inherited-rootkey-eval' \
      PGHOSTADDR=192.0.2.1 PGDATABASE=inherited_pgdatabase \
      vhh_timed "$@" \
        </dev/null >"$vhh_out/$vhh_name.out" 2>"$vhh_out/$vhh_name.err" )
    vhh_rc=$?
    echo "$vhh_rc" > "$vhh_out/$vhh_name.rc"
}

# The helper left nothing in its TMPDIR: its state directory is gone.
vhh_tmp_empty() {
    [ -z "$(ls -A "$vhh_tmp")" ] || vhh_fail "$1: left $(ls -A "$vhh_tmp" | head -n 3 | tr '\n' ' ')in TMPDIR"
}

# vhh_get FILE KEY: a top-level or dotted key of a probe report.
vhh_get() {
    "$vhh_py" -I -c '
import json, sys
value = json.load(open(sys.argv[1]))
for part in sys.argv[2].split("."):
    value = value.get(part) if isinstance(value, dict) else None
print(value if isinstance(value, str) else json.dumps(value, sort_keys=True))
' "$1" "$2"
}

# The probe report shows only throwaway configuration: no system, user or
# local file layer, and no inherited database or rootkey value anywhere.
vhh_check_isolated() {
    for layer in system user local; do
        [ "$(vhh_get "$1" "layers.$layer")" = '{}' ] \
            || vhh_fail "$2: the $layer config layer leaked in: $(vhh_get "$1" "layers.$layer")"
    done
    for marker in dev_real db.dev.invalid dev_user dev_password 6543 dev-rootkey local_real local-marker \
                  inherited_real db.inherited.invalid inherited_user inherited_password inherited_schema inherited-rootkey inherited_pgdatabase; do
        ! grep -q -- "$marker" "$1" || vhh_fail "$2: '$marker' reached the command"
    done
}

# The command saw a valid rootkey generated for the run, and no other.
vhh_check_rootkey() {
    vhh_key_seen=$(vhh_get "$1" rootkey)
    [ "$(vhh_get "$1" rootkey_valid)" = true ] || vhh_fail "$2: rootkey '$vhh_key_seen' is not a valid Fernet key"
    [ "$vhh_key_seen" = "$(vhh_get "$1" env_rootkey)" ] || vhh_fail "$2: config rootkey differs from the exported one"
}

# The command ran in the state directory under the helper's TMPDIR, saw the
# repo root, and found HOME and TMPDIR inside the state directory (the probe
# records their real paths while they exist).
vhh_check_cwd() {
    vhh_cwd=$(vhh_get "$1" cwd)
    [ "$(dirname "$vhh_cwd")" = "$(cd "$vhh_tmp" && pwd -P)" ] \
        || vhh_fail "$2: cwd $vhh_cwd is not a state directory under $vhh_tmp"
    [ "$(vhh_get "$1" repo_root)" = "$(cd "$vhh_fixture_dir" && pwd -P)" ] \
        || vhh_fail "$2: REPO_ROOT is '$(vhh_get "$1" repo_root)', not the fixture root"
    for vhh_var in home tmpdir; do
        case $(vhh_get "$1" "$vhh_var") in "$vhh_cwd"|"$vhh_cwd"/*) ;; *)
            vhh_fail "$2: $vhh_var '$(vhh_get "$1" "$vhh_var")' is outside the state directory" ;; esac
    done
}

# The fixture tree is byte-identical to its manifest from before the runs.
vhh_check_tree() {
    vhh_tag=$(printf '%s' "$1" | tr -c 'A-Za-z0-9' _)
    vhh_manifest "$vhh_fixture_dir" > "$vhh_lab/after-$vhh_tag.manifest"
    cmp -s "$vhh_lab/before.manifest" "$vhh_lab/after-$vhh_tag.manifest" \
        || vhh_fail "$1: the worktree changed: $(diff "$vhh_lab/before.manifest" "$vhh_lab/after-$vhh_tag.manifest" | grep '^[<>]' | head -n 5 | tr '\n' ' ')"
    vhh_manifest "$vhh_home" > "$vhh_lab/home-after-$vhh_tag.manifest"
    cmp -s "$vhh_lab/home-before.manifest" "$vhh_lab/home-after-$vhh_tag.manifest" \
        || vhh_fail "$1: the developer home changed: $(diff "$vhh_lab/home-before.manifest" "$vhh_lab/home-after-$vhh_tag.manifest" | grep '^[<>]' | head -n 5 | tr '\n' ' ')"
}

# Set up lab, fixture, environment, populated home and the stale-lock
# precondition; take the before-manifests.
vhh_setup() {
    vhh_lab
    vhh_fixture_dir="$vhh_lab/repo"
    vhh_home="$vhh_lab/devhome"
    vhh_out="$vhh_lab/out"
    mkdir -p "$vhh_out"
    vhh_fixture "$1" "$vhh_fixture_dir"
    vhh_env
    vhh_populate "$vhh_home" "$vhh_fixture_dir"
    # R11's precondition: the fixture's lock is out of date. --check never writes.
    ( cd "$vhh_fixture_dir" && uv lock --check --offline ) >"$vhh_lab/lock-check.out" 2>&1 \
        && vhh_fail "precondition: the fixture's uv.lock is up to date, so R11 would prove nothing"
    grep -q 'needs to be updated' "$vhh_lab/lock-check.out" \
        || vhh_fail "precondition: uv lock --check failed for another reason: $(tail -n 1 "$vhh_lab/lock-check.out")"
    vhh_manifest "$vhh_fixture_dir" > "$vhh_lab/before.manifest"
    vhh_manifest "$vhh_home" > "$vhh_lab/home-before.manifest"
}

# vhh_usage_lines HELPER: every example invocation in a helper's header (the
# generic `Usage:` synopsis aside).
vhh_usage_lines() {
    sed -n 's/^#[[:space:]]*\(.*tools\/temp_[a-z]*\.sh .*\)$/\1/p' "$1" | grep -v '<command>'
}

# A usage line must hand its command to `sh -c`, and every test path in it
# must start at "$REPO_ROOT/": the command runs in the state directory.
vhh_check_usage_form() {
    case $1 in *"tools/temp_"*".sh sh -c '"*) ;; *) vhh_fail "R7: usage line does not use sh -c: $1" ;; esac
    printf '%s' "$1" | grep -q '"\$REPO_ROOT' || vhh_fail "R7: usage line names no \$REPO_ROOT path: $1"
    if printf '%s' "$1" | sed 's#"\$REPO_ROOT[^"]*"##g' | grep -Eq '(^|[ /])tests'; then
        vhh_fail "R7: usage line has a test path not anchored at \$REPO_ROOT: $1"
    fi
}

# vhh_found_tests FILE RC: pytest found at least one test. Collection errors
# alone do not count; exit 5 (nothing collected) counts only when tests were
# deselected; exit 4 (usage error) never does.
vhh_found_tests() {
    [ "$2" != 4 ] || return 1
    grep -Eq '(^|[ =])[1-9][0-9]* (passed|failed|skipped|deselected|xfailed|xpassed|tests? collected)' "$1" || return 1
    [ "$2" != 5 ] || grep -Eq '[1-9][0-9]* deselected' "$1"
}

# vhh_stdout_is FILE TEXT: FILE holds exactly TEXT and one newline.
vhh_stdout_is() { printf '%s\n' "$2" | cmp -s - "$1"; }

# vhh_dead PID: the process is gone (allowing 5 s for a zombie to be reaped).
vhh_dead() {
    vhh_n=0
    while kill -0 "$1" 2>/dev/null; do
        vhh_n=$((vhh_n + 1)); [ "$vhh_n" -lt 10 ] || return 1
        sleep 0.5
    done
}

# vhh_nodocker_path DIR: a directory of links to every command on PATH but
# docker, so a test can remove docker without removing /usr/bin.
vhh_nodocker_path() {
    mkdir -p "$1"
    for vhh_d in $(printf '%s' "$PATH" | tr ':' ' '); do
        for vhh_f in "$vhh_d"/*; do
            vhh_b=${vhh_f##*/}
            [ "$vhh_b" != docker ] && [ -x "$vhh_f" ] && [ ! -d "$vhh_f" ] && [ ! -e "$1/$vhh_b" ] \
                && ln -s "$vhh_f" "$1/$vhh_b"
        done
    done
    return 0
}
