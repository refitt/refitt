#!/bin/sh
# P1 gate: tools/temp_db.sh meets R1, R2, R3, R5, R6, R7 and R11 on this host.
#
#   sh spec/verify-helpers-harden/verify/gate_temp_db.sh [index|head]
#
# Drives the helper as staged (default `index`) in a fixture exported to a lab,
# with a populated developer home, a repo-root local config, inherited database
# and rootkey variables, stdin from /dev/null and a stale uv.lock. Prints one
# `ok`/`FAIL` line per check and exits non-zero at the first failure.
#
# Footprint: see lib.sh. Sequential; peak one helper run (~5 processes,
# ~150 MB). Measured at planning: see TECH.md P1.
. "$(dirname -- "$0")/lib.sh"

vhh_setup "${1:-index}"
db=tools/temp_db.sh

# R1, R2, R3, R6, R7 in one run: no terminal, populated home, inherited variables.
vhh_run probe "$db" sh -c 'uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/probe.json" && printf "cmd-out\n"'
[ "$vhh_rc" = 0 ] || vhh_fail "R1: exit $vhh_rc with stdin from /dev/null: $(tail -n 3 "$vhh_out/probe.err" | tr '\n' ' ')"
[ "$(vhh_get "$vhh_out/probe.json" users)" -gt 0 ] 2>/dev/null || vhh_fail "R1: the throwaway database holds no seeded users"
[ "$(vhh_get "$vhh_out/probe.json" database.provider)" = sqlite ] || vhh_fail "R2: provider is not sqlite"
vhh_ok "R1 seeded and ran with no terminal"
vhh_check_isolated "$vhh_out/probe.json" R2
vhh_ok "R2 no system, user or local config value; no inherited database value"
vhh_check_rootkey "$vhh_out/probe.json" R3
key1=$(vhh_get "$vhh_out/probe.json" rootkey)
vhh_stdout_is "$vhh_out/probe.out" cmd-out || vhh_fail "R6: stdout is not exactly the command's: $(head -c 200 "$vhh_out/probe.out")"
vhh_ok "R6 stdout carries only the command's output"
vhh_check_cwd "$vhh_out/probe.json" R7
vhh_ok "R7 command ran in the state directory and saw REPO_ROOT"
vhh_tmp_empty "R5 success"

# R3: a second run gets a different rootkey.
vhh_run probe2 "$db" sh -c 'uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/probe2.json"'
[ "$vhh_rc" = 0 ] || vhh_fail "R3: second run exit $vhh_rc"
vhh_check_rootkey "$vhh_out/probe2.json" R3
[ "$(vhh_get "$vhh_out/probe2.json" rootkey)" != "$key1" ] || vhh_fail "R3: two runs saw the same rootkey"
vhh_ok "R3 each run gets its own valid rootkey; inherited and developer keys never reach the command"

# R5 + R6: the command's failure status passes through and cleanup still happens.
vhh_run fail "$db" sh -c 'printf "partial\n"; exit 7'
[ "$vhh_rc" = 7 ] || vhh_fail "R6: exit $vhh_rc, the command exited 7"
vhh_stdout_is "$vhh_out/fail.out" partial || vhh_fail "R6: stdout on failure is not exactly the command's"
vhh_tmp_empty "R5 command failure"
vhh_ok "R5/R6 a failing command's status passes through; state removed"

# R5: the seed fails, the command never runs, and cleanup still happens.
vhh_run seedfail env REFITT_TEMP_DB_INIT=--no-such-flag "$db" sh -c 'touch "$VHH_OUT/seedfail.ran"'
[ "$vhh_rc" != 0 ] || vhh_fail "R5: a failed seed exited 0"
[ ! -e "$vhh_out/seedfail.ran" ] || vhh_fail "R5: the command ran after a failed seed"
[ ! -s "$vhh_out/seedfail.out" ] || vhh_fail "R6: a failed seed wrote to stdout"
vhh_tmp_empty "R5 seed failure"
vhh_ok "R5 a failed seed exits non-zero, runs nothing, removes state"

# R5: a command that leaves a read-only directory in its TMPDIR (pytest does).
vhh_run readonly "$db" sh -c 'mkdir -p "$TMPDIR/ro/sub" && chmod 500 "$TMPDIR/ro" && exit 3'
[ "$vhh_rc" = 3 ] || vhh_fail "R5/R6: exit $vhh_rc after a read-only leftover, the command exited 3"
vhh_tmp_empty "R5 read-only leftover"
vhh_ok "R5 read-only leftovers are removed; the status still passes through"

# R7/R11: with no project environment the helper refuses, and creates none in the worktree.
vhh_run noenv env -u UV_PROJECT_ENVIRONMENT "$db" sh -c 'touch "$VHH_OUT/noenv.ran"'
[ "$vhh_rc" != 0 ] || vhh_fail "preflight: exit 0 with no project environment"
grep -q 'no environment' "$vhh_out/noenv.err" || vhh_fail "preflight: no message naming the missing environment"
[ ! -e "$vhh_out/noenv.ran" ] && [ ! -e "$vhh_fixture_dir/.venv" ] || vhh_fail "preflight: the command ran or a .venv appeared"
vhh_tmp_empty "preflight"
vhh_ok "R7/R11 no environment: refused before anything was created; no .venv in the worktree"

# R5: INT, TERM, and TERM sent twice stop the command's process group and remove state.
for sig in TERM INT TERM2; do
    sigdir="$vhh_out/$sig"
    mkdir -p "$sigdir"
    vhh_tmp="$vhh_lab/tmp-sig-$sig"
    mkdir -p "$vhh_tmp"
    ( cd "$vhh_fixture_dir" && HOME="$vhh_home" TMPDIR="$vhh_tmp" VHH_SIG="$sigdir" \
      exec perl -e '$SIG{INT} = "DEFAULT"; exec { $ARGV[0] } @ARGV' "$db" \
        sh -c 'trap "" TERM; sleep 60 & echo $! > "$VHH_SIG/child"; echo $$ > "$VHH_SIG/cmd"; wait' \
        </dev/null >"$sigdir/out" 2>"$sigdir/err" ) &
    helper=$!
    n=0
    until [ -s "$sigdir/child" ] && [ -s "$sigdir/cmd" ]; do
        n=$((n + 1)); [ "$n" -lt 120 ] || vhh_fail "R5 $sig: the command never started"
        sleep 0.5
    done
    case $sig in
        TERM) kill -TERM "$helper"; want=143 ;;
        INT) kill -INT "$helper"; want=130 ;;
        # The command ignores TERM, so teardown waits on the KILL watchdog;
        # a second TERM lands in the middle of it.
        TERM2) kill -TERM "$helper"; sleep 1; kill -TERM "$helper" 2>/dev/null; want=143 ;;
    esac
    wait "$helper"; rc=$?
    [ "$rc" = "$want" ] || vhh_fail "R5 $sig: helper exited $rc, expected $want"
    for who in cmd child; do
        vhh_dead "$(cat "$sigdir/$who")" || vhh_fail "R5 $sig: the command's $who is still running"
    done
    vhh_tmp_empty "R5 $sig"
    vhh_ok "R5 $sig stops the command's process group and removes state"
done

# Stdin still reaches the command.
vhh_tmp="$vhh_lab/tmp-stdin"; mkdir -p "$vhh_tmp"
got=$(cd "$vhh_fixture_dir" && printf 'piped-in\n' | HOME="$vhh_home" TMPDIR="$vhh_tmp" "$db" cat 2>/dev/null)
[ "$got" = piped-in ] || vhh_fail "stdin: the command read '$got'"
vhh_tmp_empty "stdin"
vhh_ok "stdin passes through to the command"

# R7: every example in the header uses sh -c, is root-anchored, and finds its tests.
lines=$(vhh_usage_lines "$vhh_fixture_dir/$db")
[ -n "$lines" ] || vhh_fail "R7: no example usage line in $db"
i=0
printf '%s\n' "$lines" | while IFS= read -r line; do
    i=$((i + 1))
    vhh_check_usage_form "$line"
    vhh_run "usage$i" sh -c "$line"
    vhh_found_tests "$vhh_out/usage$i.out" "$vhh_rc" || vhh_fail "R7: usage line found no tests (exit $vhh_rc): $line"
    vhh_tmp_empty "R5 usage line"
    vhh_ok "R7 usage line finds its tests: $line"
done || exit 1

# R7 + R11: after every run above, the fixture and the developer home are unchanged.
vhh_check_tree "R7/R11"
vhh_ok "R7/R11 worktree byte-identical (stale uv.lock included); developer home untouched"
printf 'PASS gate_temp_db\n'
