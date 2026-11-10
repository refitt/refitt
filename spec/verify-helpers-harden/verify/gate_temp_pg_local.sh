#!/bin/sh
# P2 gate: what of tools/temp_pg.sh can be proven on a host with no Docker and
# no Postgres.
#
#   sh spec/verify-helpers-harden/verify/gate_temp_pg_local.sh [index|head]
#
# Proves R9 (no daemon: stop before starting anything, naming REFITT_TEST_PG=1)
# with docker absent and with a docker whose daemon does not answer. The rest
# runs in REFITT_TEST_PG=1 mode with uv's two Postgres-bound calls stubbed
# (`refitt database init` and `refitt-server start`): it exercises the
# helper's own logic for R2, R3, R5, R6, R7, R11, the dev server's readiness
# wait and teardown, and the PGTZ export. It is supporting evidence only: it
# verifies no container-mode R-ID, and no seed. The container drive
# (container_drive.sh, on a Docker host) is the evidence for R4, R5, R8, R10 and
# for every R-ID in container mode.
#
# Footprint: see lib.sh. Sequential; peak one helper run plus a stub HTTP
# server (~6 processes, ~200 MB). Measured at planning: see TECH.md P2; 30 s
# of it is the dev-server timeout case, up to 10 s the wedged-daemon case.
. "$(dirname -- "$0")/lib.sh"

vhh_setup "${1:-index}"
pg=tools/temp_pg.sh

# R9, docker absent: a PATH of links to everything but docker (removing whole
# directories would take /usr/bin with it on Linux).
nodock="$vhh_lab/bin-nodocker"
vhh_nodocker_path "$nodock"
! PATH=$nodock command -v docker >/dev/null 2>&1 || vhh_fail "precondition: docker still on the trimmed PATH"
vhh_run nodocker env PATH="$nodock" "$pg" sh -c 'touch "$VHH_OUT/nodocker.ran"'
[ "$vhh_rc" != 0 ] || vhh_fail "R9: exit 0 with no docker"
grep -q 'REFITT_TEST_PG=1' "$vhh_out/nodocker.err" || vhh_fail "R9: stderr does not name REFITT_TEST_PG=1: $(cat "$vhh_out/nodocker.err")"
[ ! -e "$vhh_out/nodocker.ran" ] || vhh_fail "R9: the command ran"
[ ! -s "$vhh_out/nodocker.out" ] || vhh_fail "R6: stdout written with no docker"
[ ! -e "$vhh_fixture_dir/.venv" ] || vhh_fail "R9: a .venv appeared"
vhh_tmp_empty "R9 no docker"
vhh_ok "R9 no docker binary: non-zero, names REFITT_TEST_PG=1, nothing started"

# R9, a docker whose daemon does not answer: only `docker info` may be called.
fakebin="$vhh_lab/fakebin"
mkdir -p "$fakebin"
cat > "$fakebin/docker" <<'EOF'
#!/bin/sh
printf '%s\n' "$1" >> "$VHH_FAKE_LOG"
if [ "$1" = info ] && [ "${VHH_FAKE_DOCKER:-}" = hang ]; then
    exec sleep 120
fi
if [ "$1" = info ]; then
    echo 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?' >&2
    exit 1
fi
exit 0
EOF
chmod +x "$fakebin/docker"
vhh_run deaddaemon env PATH="$fakebin:$nodock" VHH_FAKE_LOG="$vhh_lab/docker.log" "$pg" sh -c 'touch "$VHH_OUT/deaddaemon.ran"'
[ "$vhh_rc" != 0 ] || vhh_fail "R9: exit 0 with a dead daemon"
grep -q 'REFITT_TEST_PG=1' "$vhh_out/deaddaemon.err" || vhh_fail "R9: stderr does not name REFITT_TEST_PG=1"
[ -s "$vhh_lab/docker.log" ] || vhh_fail "R9: the daemon was never asked"
[ -z "$(grep -vE '^(info|version)$' "$vhh_lab/docker.log")" ] || vhh_fail "R9: docker called beyond info: $(sort -u "$vhh_lab/docker.log" | tr '\n' ' ')"
[ ! -e "$vhh_out/deaddaemon.ran" ] || vhh_fail "R9: the command ran"
[ ! -s "$vhh_out/deaddaemon.out" ] || vhh_fail "R6: stdout written with a dead daemon"
vhh_tmp_empty "R9 dead daemon"
vhh_ok "R9 dead daemon: non-zero, names REFITT_TEST_PG=1, only 'docker info' called, nothing started"

# R9, a daemon that never answers: the check itself is bounded.
: > "$vhh_lab/docker.log"
start=$(date +%s)
vhh_run wedged env PATH="$fakebin:$nodock" VHH_FAKE_LOG="$vhh_lab/docker.log" VHH_FAKE_DOCKER=hang "$pg" sh -c 'touch "$VHH_OUT/wedged.ran"'
took=$(( $(date +%s) - start ))
[ "$vhh_rc" != 0 ] && [ "$took" -lt 60 ] || vhh_fail "R9: a wedged daemon gave exit $vhh_rc after ${took}s"
grep -q 'REFITT_TEST_PG=1' "$vhh_out/wedged.err" || vhh_fail "R9: no REFITT_TEST_PG=1 message for a wedged daemon"
[ ! -e "$vhh_out/wedged.ran" ] || vhh_fail "R9: the command ran"
vhh_tmp_empty "R9 wedged daemon"
vhh_ok "R9 wedged daemon: non-zero after ${took}s, names REFITT_TEST_PG=1"

# Stubs for REFITT_TEST_PG=1 mode: init succeeds without a database; the dev
# server is a plain HTTP server (or one that never answers, with VHH_FAKE_SERVER=hang).
real_uv=$(command -v uv)
cat > "$fakebin/uv" <<'EOF'
#!/bin/sh
case " $* " in
    *" refitt database init "*)
        printf 'init %s\n' "$*" >> "$VHH_FAKE_LOG"
        [ "${VHH_FAKE_INIT:-}" = fail ] && exit 6
        exit 0 ;;
    *" refitt-server start "*)
        echo $$ >> "$VHH_FAKE_SERVER_PIDS"
        port=$(printf '%s\n' "$@" | sed -n '/^--port$/{n;p;}')
        [ "${VHH_FAKE_SERVER:-}" = hang ] && exec sleep 1000
        exec "$VHH_PY" -I -m http.server --bind 127.0.0.1 "$port" ;;
esac
exec "$VHH_REAL_UV" "$@"
EOF
chmod +x "$fakebin/uv"
# Runs its arguments with the stubs first on PATH and REFITT_TEST_PG=1 settings.
cat > "$vhh_lab/stubenv" <<EOF
#!/bin/sh
exec env PATH="$fakebin:$nodock" VHH_REAL_UV="$real_uv" VHH_PY="$vhh_py" \\
    VHH_FAKE_LOG="$vhh_lab/uv.log" VHH_FAKE_SERVER_PIDS="$vhh_lab/server.pids" \\
    VHH_PROBE_NO_DB=1 REFITT_TEST_PG=1 \\
    REFITT_DATABASE_DEFAULT_HOST=127.0.0.1 REFITT_DATABASE_DEFAULT_PORT=55432 \\
    REFITT_DATABASE_DEFAULT_DATABASE=scratch_db REFITT_DATABASE_DEFAULT_USER=scratch_user \\
    REFITT_DATABASE_DEFAULT_PASSWORD=scratch_pw "\$@"
EOF
chmod +x "$vhh_lab/stubenv"
stub="$vhh_lab/stubenv"
servers_dead() {
    [ -s "$vhh_lab/server.pids" ] || vhh_fail "$1: the dev server stub never started"
    while read -r spid; do
        vhh_dead "$spid" || vhh_fail "$1: dev server $spid still running"
    done < "$vhh_lab/server.pids"
}

vhh_run stubbed "$stub" env REFITT_TEMP_WITH_SERVER=1 VHH_PROBE_HTTP=1 "$pg" \
    sh -c 'uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/stubbed.json" && printf "cmd-out\n"'
[ "$vhh_rc" = 0 ] || vhh_fail "stubbed run exit $vhh_rc: $(tail -n 3 "$vhh_out/stubbed.err" | tr '\n' ' ')"
j="$vhh_out/stubbed.json"
vhh_check_isolated "$j" "R2 (stubbed)"
[ "$(vhh_get "$j" database.host)/$(vhh_get "$j" database.database)" = 127.0.0.1/scratch_db ] \
    || vhh_fail "REFITT_TEST_PG=1: the scratch database settings did not reach the command"
vhh_check_rootkey "$j" "R3 (stubbed)"
vhh_stdout_is "$vhh_out/stubbed.out" cmd-out || vhh_fail "R6 (stubbed): stdout is not exactly the command's"
vhh_check_cwd "$j" "R7 (stubbed)"
[ "$(vhh_get "$j" pgtz)" = America/Indiana/Indianapolis ] || vhh_fail "PGTZ is '$(vhh_get "$j" pgtz)'"
[ "$(vhh_get "$j" server_answered)" = true ] || vhh_fail "the command ran before the dev server answered"
grep -q '^init .*--drop --test' "$vhh_lab/uv.log" || vhh_fail "the scratch database was not initialized with --drop --test"
servers_dead "R5 (stubbed)"
vhh_tmp_empty "R5 (stubbed)"
vhh_ok "REFITT_TEST_PG=1 with stubs: isolated config, own rootkey, clean stdout, state cwd, PGTZ, server answered first, all torn down"

# R3 with no server: the rootkey is not tied to REFITT_TEMP_WITH_SERVER.
vhh_run noserver "$stub" "$pg" sh -c 'uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/noserver.json"'
[ "$vhh_rc" = 0 ] || vhh_fail "R3 (stubbed, no server): exit $vhh_rc"
vhh_check_rootkey "$vhh_out/noserver.json" "R3 (stubbed, no server)"
[ "$(vhh_get "$vhh_out/noserver.json" rootkey)" != "$(vhh_get "$j" rootkey)" ] || vhh_fail "R3: two runs saw the same rootkey"
vhh_tmp_empty "R5 (stubbed, no server)"
vhh_ok "R3 a fresh valid rootkey with no server too"

# R5: the seed fails: non-zero, the command and the server never start.
: > "$vhh_lab/server.pids"
vhh_run initfail "$stub" env VHH_FAKE_INIT=fail REFITT_TEMP_WITH_SERVER=1 "$pg" sh -c 'touch "$VHH_OUT/initfail.ran"'
[ "$vhh_rc" != 0 ] || vhh_fail "R5: a failed seed exited 0"
[ ! -e "$vhh_out/initfail.ran" ] && [ ! -s "$vhh_out/initfail.out" ] || vhh_fail "R5/R6: the command ran or stdout was written"
[ ! -s "$vhh_lab/server.pids" ] || vhh_fail "R5: the dev server started after a failed seed"
vhh_tmp_empty "R5 (stubbed, seed fails)"
vhh_ok "R5 a failed seed: non-zero, nothing run, state removed"

# R7: the profile's verify and the release gate, as AGENTS.md states them,
# collect tests from the state directory (collection only, via PYTEST_ADDOPTS).
anchored=$(sed -n 's/.*`\(REFITT_TEMP_WITH_SERVER=1 tools\/temp_pg\.sh sh -c .*"\$REPO_ROOT"'"'"'\) && make.*/\1/p' "$vhh_fixture_dir/AGENTS.md" | head -n 1)
[ -n "$anchored" ] || vhh_fail "R7: no root-anchored temp_pg.sh invocation in the profile's verify"
: > "$vhh_lab/server.pids"
vhh_run verifyline "$stub" env PYTEST_ADDOPTS='--collect-only -q' sh -c "$anchored"
vhh_found_tests "$vhh_out/verifyline.out" "$vhh_rc" || vhh_fail "R7: the profile's verify collected no tests (exit $vhh_rc)"
servers_dead "R5 (verify line)"
vhh_tmp_empty "R5 (verify line)"
vhh_ok "R7 the profile's verify finds its tests from the state directory: $anchored"

# Teardown on TERM while the dev server runs.
sigdir="$vhh_out/term"; mkdir -p "$sigdir"
vhh_tmp="$vhh_lab/tmp-term"; mkdir -p "$vhh_tmp"
: > "$vhh_lab/server.pids"
( cd "$vhh_fixture_dir" && HOME="$vhh_home" TMPDIR="$vhh_tmp" VHH_SIG="$sigdir" REFITT_TEMP_WITH_SERVER=1 \
  exec "$stub" perl -e '$SIG{INT} = "DEFAULT"; exec { $ARGV[0] } @ARGV' "$pg" \
    sh -c 'sleep 60 & echo $! > "$VHH_SIG/child"; echo $$ > "$VHH_SIG/cmd"; wait' \
    </dev/null >"$sigdir/out" 2>"$sigdir/err" ) &
helper=$!
n=0
until [ -s "$sigdir/child" ] && [ -s "$sigdir/cmd" ]; do
    n=$((n + 1)); [ "$n" -lt 120 ] || vhh_fail "R5 TERM (stubbed): the command never started"
    sleep 0.5
done
kill -TERM "$helper"
wait "$helper"; rc=$?
[ "$rc" = 143 ] || vhh_fail "R5 TERM (stubbed): helper exited $rc"
for who in cmd child; do
    vhh_dead "$(cat "$sigdir/$who")" || vhh_fail "R5 TERM (stubbed): the command's $who is still running"
done
servers_dead "R5 TERM (stubbed)"
vhh_tmp_empty "R5 TERM (stubbed)"
vhh_ok "TERM with the dev server up: command group, server and state all gone"

# A dev server that never answers: bounded wait, a message naming it, teardown.
: > "$vhh_lab/server.pids"
start=$(date +%s)
# A proxy that answers 502 to everything must not count as the server answering.
proxy_port=$("$vhh_py" -I -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')
"$vhh_py" -I -c '
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(502); self.end_headers()
    def log_message(self, *args):
        pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
' "$proxy_port" >/dev/null 2>&1 &
proxy=$!
n=0
until "$vhh_py" -I -c 'import socket, sys; socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1)' "$proxy_port" 2>/dev/null; do
    n=$((n + 1)); [ "$n" -lt 20 ] || vhh_fail "precondition: the 502 proxy never listened"
    sleep 0.5
done
vhh_run hang "$stub" env REFITT_TEMP_WITH_SERVER=1 VHH_FAKE_SERVER=hang \
    http_proxy="http://127.0.0.1:$proxy_port" HTTP_PROXY="http://127.0.0.1:$proxy_port" no_proxy= NO_PROXY= \
    "$pg" sh -c 'touch "$VHH_OUT/hang.ran"'
took=$(( $(date +%s) - start ))
[ "$vhh_rc" != 0 ] || vhh_fail "a dev server that never answers: exit 0"
grep -q 'dev server' "$vhh_out/hang.err" || vhh_fail "the timeout message does not name the dev server: $(tail -n 1 "$vhh_out/hang.err")"
[ ! -e "$vhh_out/hang.ran" ] || vhh_fail "the command ran before the dev server answered"
[ "$took" -lt 90 ] || vhh_fail "the dev-server wait took ${took}s, not bounded near 30 s"
servers_dead "dev-server timeout"
vhh_tmp_empty "dev-server timeout"
kill "$proxy" 2>/dev/null
vhh_ok "a silent dev server behind a 502 proxy: non-zero after ${took}s, named on stderr, torn down"

# R7: temp_pg.sh's examples use sh -c and are root-anchored (they run in the container drive).
lines=$(vhh_usage_lines "$vhh_fixture_dir/$pg")
[ -n "$lines" ] || vhh_fail "R7: no example usage line in $pg"
printf '%s\n' "$lines" | while IFS= read -r line; do vhh_check_usage_form "$line"; done || exit 1
vhh_ok "R7 temp_pg.sh usage lines use sh -c and are root-anchored"

vhh_check_tree "R11 (stubbed)"
vhh_ok "R11 worktree byte-identical (stale uv.lock included); developer home untouched"
printf 'PASS gate_temp_pg_local\n'
