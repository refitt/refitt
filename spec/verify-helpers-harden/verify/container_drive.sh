#!/bin/sh
# Container-mode drive for verify-helpers-harden, run on a Docker host before
# review (GOAL Clarification Q2). From the root of a checkout of the cycle
# branch's tip:
#
#   sh spec/verify-helpers-harden/verify/container_drive.sh
#
# It drives tools/temp_pg.sh as committed (HEAD) in a fixture exported to a lab,
# with a populated developer home, a repo-root local config, inherited database
# and rootkey variables, a host TZ unlike the seed's, stdin from /dev/null and a
# stale uv.lock. It covers R4, R5, R8 and R10, and R2, R3, R6, R7 and R11 in
# container mode; then R2, R3, R5, R6, R7, R10 and R11 in REFITT_TEST_PG=1 mode
# against a scratch Postgres container of its own. One `ok`/`FAIL` line per
# check; exit 0 only if every check passed, ending `PASS container_drive`.
#
# Needs: a Docker daemon, uv, perl, git, and network access to PyPI (the gate
# environment, first run only) and to Docker Hub (postgres:16 and
# nginx:1.27-alpine). No libpq or librdkafka: the environment uses the
# psycopg2-binary wheel and skips confluent-kafka (see lib.sh).
#
# Footprint: see lib.sh. Sequential but for one check that runs two helpers at
# once; peak two Postgres containers, two dev servers and two Python processes
# (~1.5 GB). Measured: not yet (no Docker host at planning); expect 4-6 min
# warm, the bring-up timeout check alone 60-90 s.
. "$(dirname -- "$0")/lib.sh"

command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 \
    || vhh_fail "precondition: no Docker daemon answers on this host"
# The helpers' HOME is the populated developer home in this drive, so pin the
# real Docker endpoint and client config for every docker call below.
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
DOCKER_HOST=${DOCKER_HOST:-$(docker context inspect -f '{{.Endpoints.docker.Host}}' 2>/dev/null)}
export DOCKER_CONFIG DOCKER_HOST

vhh_setup head
pg=tools/temp_pg.sh
zone=America/Indiana/Indianapolis
label=refitt.temp-pg.state

# Every container and volume on the daemon, not only the helper's labelled
# ones: a helper that dropped its label, or `-v`, would leak unseen otherwise.
# Run the drive alone on the daemon.
docker_state() { { docker ps -aq --no-trunc | sed 's/^/container /'; docker volume ls -q | sed 's/^/volume /'; } | sort; }
docker_state > "$vhh_lab/docker.before"
no_new_containers() {
    docker_state > "$vhh_lab/docker.now"
    cmp -s "$vhh_lab/docker.before" "$vhh_lab/docker.now" \
        || vhh_fail "$1: outlived its run: $(comm -13 "$vhh_lab/docker.before" "$vhh_lab/docker.now" | tr '\n' ' ')"
}
port_closed() {
    "$vhh_py" -I -c 'import socket, sys; socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=2)' "$2" 2>/dev/null \
        && vhh_fail "$1: something still listens on dev-server port $2"
    return 0
}

# The command every container-mode run uses: record the container's published
# ports and server time zone, then probe.
probe_cmd='ctr="refitt-temp-pg-${PWD##*.}"
docker port "$ctr" 5432/tcp > "$VHH_OUT/$VHH_NAME.ports"
docker exec "$ctr" psql -U refitt -d refitt_test -Atc "SHOW timezone" > "$VHH_OUT/$VHH_NAME.servertz"
uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/$VHH_NAME.json" && printf "cmd-out\n"'

check_container_run() {  # NAME: R2-R4, R6-R8, R10 for one probe run
    j="$vhh_out/$1.json"
    [ "$(cat "$vhh_out/$1.rc")" = 0 ] || vhh_fail "$1: exit $(cat "$vhh_out/$1.rc"): $(tail -n 3 "$vhh_out/$1.err" | tr '\n' ' ')"
    ports=$(cat "$vhh_out/$1.ports")
    case $ports in 127.0.0.1:[0-9]*) ;; *) vhh_fail "R8 $1: Postgres published as '$ports', not only on 127.0.0.1" ;; esac
    [ "$(printf '%s\n' "$ports" | wc -l | tr -d ' ')" = 1 ] || vhh_fail "R8 $1: more than one published address: $ports"
    [ "$(vhh_get "$j" database.host):$(vhh_get "$j" database.port)" = "$ports" ] \
        || vhh_fail "R4 $1: the command's database is $(vhh_get "$j" database.host):$(vhh_get "$j" database.port), the container is $ports"
    [ "$(vhh_get "$j" users)" -gt 0 ] 2>/dev/null || vhh_fail "R4 $1: the container holds no seeded users"
    vhh_check_isolated "$j" "R2/R4 $1"
    vhh_check_rootkey "$j" "R3 $1"
    vhh_stdout_is "$vhh_out/$1.out" cmd-out || vhh_fail "R6 $1: stdout is not exactly the command's"
    [ "$(vhh_get "$j" session_timezone)" = "$zone" ] || vhh_fail "R10 $1: libpq session zone is $(vhh_get "$j" session_timezone)"
    [ "$(cat "$vhh_out/$1.servertz")" = "$zone" ] || vhh_fail "R10 $1: the server default zone is $(cat "$vhh_out/$1.servertz")"
}
check_torn_down() {  # NAME
    vhh_tmp="$vhh_lab/tmp-$1"
    vhh_tmp_empty "R5 $1"
    no_new_containers "R5 $1"
    if [ -f "$vhh_out/$1.json" ] && [ "$(vhh_get "$vhh_out/$1.json" api_port)" != null ]; then
        port_closed "R5 $1" "$(vhh_get "$vhh_out/$1.json" api_port)"
    fi
}

# Container mode, the full path: server on, host TZ unlike the seed's.
vhh_run main env TZ=Asia/Tokyo REFITT_TEMP_WITH_SERVER=1 VHH_PROBE_HTTP=1 VHH_NAME=main "$pg" sh -c "$probe_cmd"
check_container_run main
[ "$(vhh_get "$vhh_out/main.json" server_answered)" = true ] || vhh_fail "R8 main: the dev server did not answer the command"
vhh_check_cwd "$vhh_out/main.json" "R7 main"
check_torn_down main
vhh_ok "container mode: its own container on 127.0.0.1, seeded, isolated, own rootkey, zone $zone, server answered, all torn down"

# R3: other runs, other rootkeys, with the server and without. R8: two runs
# at once both succeed (c2 has no server, so R3 is seen without one).
( vhh_run c1 env REFITT_TEMP_WITH_SERVER=1 VHH_PROBE_HTTP=1 VHH_NAME=c1 "$pg" sh -c "$probe_cmd" ) &
w1=$!
( vhh_run c2 env VHH_NAME=c2 "$pg" sh -c "$probe_cmd" ) &
w2=$!
wait "$w1"; wait "$w2"
check_container_run c1
check_container_run c2
[ "$(cat "$vhh_out/c1.ports")" != "$(cat "$vhh_out/c2.ports")" ] || vhh_fail "R8: concurrent runs shared a Postgres port"
for k in c1 c2; do
    [ "$(vhh_get "$vhh_out/$k.json" rootkey)" != "$(vhh_get "$vhh_out/main.json" rootkey)" ] || vhh_fail "R3: $k reused a rootkey"
    check_torn_down "$k"
done
vhh_ok "R8 two concurrent runs both succeed on distinct ports; R3 each run its own rootkey"

# R5/R6: the command fails.
vhh_run fail "$pg" sh -c 'printf "partial\n"; exit 7'
[ "$vhh_rc" = 7 ] || vhh_fail "R6: exit $vhh_rc, the command exited 7"
vhh_stdout_is "$vhh_out/fail.out" partial || vhh_fail "R6: stdout on failure is not exactly the command's"
check_torn_down fail
vhh_ok "R5/R6 a failing command's status passes through; container and state removed"

# R5: the seed fails after the container started (a uv shim fails only
# `refitt database init`; everything else reaches the real uv).
shim="$vhh_lab/shim"; mkdir -p "$shim"
real_uv=$(command -v uv)
cat > "$shim/uv" <<EOF
#!/bin/sh
case " \$* " in *" refitt database init "*) echo "shim: init fails" >&2; exit 6 ;; esac
exec "$real_uv" "\$@"
EOF
chmod +x "$shim/uv"
vhh_run seedfail env PATH="$shim:$PATH" "$pg" sh -c 'touch "$VHH_OUT/seedfail.ran"'
grep -q 'shim: init fails' "$vhh_out/seedfail.err" || vhh_fail "precondition: the seed failure was not the shim's"
[ "$vhh_rc" != 0 ] || vhh_fail "R5: a failed bring-up exited 0"
[ ! -e "$vhh_out/seedfail.ran" ] && [ ! -s "$vhh_out/seedfail.out" ] || vhh_fail "R5/R6: the command ran or stdout was written"
check_torn_down seedfail
vhh_ok "R5 the seed fails after the container started: non-zero, container and state removed"

# R8/R5: Postgres never accepts a connection (a long-running image that is not Postgres).
start=$(date +%s)
vhh_run silent env REFITT_TEST_PG_IMAGE=nginx:1.27-alpine "$pg" sh -c 'touch "$VHH_OUT/silent.ran"'
took=$(( $(date +%s) - start ))
[ "$vhh_rc" != 0 ] || vhh_fail "R8: exit 0 when Postgres never answered"
grep -q 'Postgres' "$vhh_out/silent.err" || vhh_fail "R8: the timeout message does not name Postgres: $(tail -n 1 "$vhh_out/silent.err")"
[ ! -e "$vhh_out/silent.ran" ] || vhh_fail "R8: the command ran before Postgres answered"
[ "$took" -ge 55 ] && [ "$took" -lt 150 ] || vhh_fail "R8: the bounded wait took ${took}s (expected about 60 s)"
check_torn_down silent
vhh_ok "R8 Postgres never ready: non-zero after ${took}s, named on stderr; container and state removed"

# R5: INT and TERM with the server up.
for sig in TERM INT; do
    sigdir="$vhh_out/$sig"; mkdir -p "$sigdir"
    vhh_tmp="$vhh_lab/tmp-$sig"; mkdir -p "$vhh_tmp"
    ( cd "$vhh_fixture_dir" && HOME="$vhh_home" TMPDIR="$vhh_tmp" VHH_SIG="$sigdir" REFITT_TEMP_WITH_SERVER=1 \
      exec perl -e '$SIG{INT} = "DEFAULT"; exec { $ARGV[0] } @ARGV' "$pg" \
        sh -c 'echo "$REFITT_API_PORT" > "$VHH_SIG/port"; sleep 60 & echo $! > "$VHH_SIG/child"; echo $$ > "$VHH_SIG/cmd"; wait' \
        </dev/null >"$sigdir/out" 2>"$sigdir/err" ) &
    helper=$!
    n=0
    until [ -s "$sigdir/child" ] && [ -s "$sigdir/cmd" ]; do
        n=$((n + 1)); [ "$n" -lt 240 ] || vhh_fail "R5 $sig: the command never started"
        sleep 0.5
    done
    kill -"$sig" "$helper"
    wait "$helper"; rc=$?
    case $sig in TERM) want=143 ;; INT) want=130 ;; esac
    [ "$rc" = "$want" ] || vhh_fail "R5 $sig: helper exited $rc, expected $want"
    for who in cmd child; do
        vhh_dead "$(cat "$sigdir/$who")" || vhh_fail "R5 $sig: the command's $who is still running"
    done
    vhh_tmp_empty "R5 $sig"
    no_new_containers "R5 $sig"
    port_closed "R5 $sig" "$(cat "$sigdir/port")"
    vhh_ok "R5 $sig: command group, dev server, container and state all gone"
done

# R7: temp_pg.sh's usage lines find their tests.
lines=$(vhh_usage_lines "$vhh_fixture_dir/$pg")
[ -n "$lines" ] || vhh_fail "R7: no example usage line in $pg"
i=0
printf '%s\n' "$lines" | while IFS= read -r line; do
    i=$((i + 1))
    vhh_check_usage_form "$line"
    VHH_BUDGET=600 vhh_run "usage$i" sh -c "$line"
    vhh_found_tests "$vhh_out/usage$i.out" "$vhh_rc" || vhh_fail "R7: usage line found no tests (exit $vhh_rc): $line"
    check_torn_down "usage$i"
    vhh_ok "R7 usage line finds its tests: $line"
done || exit 1

# R7: the profile's verify and the release gate, as AGENTS.md states them, find
# their tests from the state directory (collection only, via PYTEST_ADDOPTS).
anchored=$(sed -n 's/.*`\(REFITT_TEMP_WITH_SERVER=1 tools\/temp_pg\.sh sh -c .*"\$REPO_ROOT"'"'"'\) && make.*/\1/p' "$vhh_fixture_dir/AGENTS.md" | head -n 1)
[ -n "$anchored" ] || vhh_fail "R7: no root-anchored temp_pg.sh invocation in the profile's verify"
vhh_run verifyline env PYTEST_ADDOPTS='--collect-only -q' sh -c "$anchored"
vhh_found_tests "$vhh_out/verifyline.out" "$vhh_rc" || vhh_fail "R7: the profile's verify collected no tests (exit $vhh_rc)"
check_torn_down verifyline
vhh_ok "R7 the profile's verify finds its tests: $anchored"

# REFITT_TEST_PG=1 mode, for real, against a scratch Postgres of the drive's own.
scratch="vhh-scratch-${vhh_lab##*.}"
trap 'docker rm -f -v "$scratch" >/dev/null 2>&1' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker run -d --name "$scratch" -e POSTGRES_DB=scratch_db -e POSTGRES_USER=scratch_user \
    -e POSTGRES_PASSWORD=scratch_pw -p 127.0.0.1::5432 postgres:16 >/dev/null \
    || vhh_fail "precondition: could not start the scratch Postgres"
sport=$(docker port "$scratch" 5432/tcp | sed -n 's/^127\.0\.0\.1:\([0-9][0-9]*\)$/\1/p' | head -n 1)
n=0
until HOME="$vhh_lab" "$vhh_py" -I -c 'import psycopg2, sys; psycopg2.connect(host="127.0.0.1", port=sys.argv[1], dbname="scratch_db", user="scratch_user", password="scratch_pw", connect_timeout=2).close()' "$sport" 2>/dev/null; do
    n=$((n + 1)); [ "$n" -lt 60 ] || vhh_fail "precondition: the scratch Postgres never answered"
    sleep 1
done
vhh_run scratch env TZ=Asia/Tokyo REFITT_TEST_PG=1 REFITT_TEMP_WITH_SERVER=1 VHH_PROBE_HTTP=1 \
    REFITT_DATABASE_DEFAULT_HOST=127.0.0.1 REFITT_DATABASE_DEFAULT_PORT="$sport" \
    REFITT_DATABASE_DEFAULT_DATABASE=scratch_db REFITT_DATABASE_DEFAULT_USER=scratch_user \
    REFITT_DATABASE_DEFAULT_PASSWORD=scratch_pw \
    "$pg" sh -c 'uv run python -I "$VHH_DIR/config_probe.py" "$VHH_OUT/scratch.json" && printf "cmd-out\n"'
j="$vhh_out/scratch.json"
[ "$vhh_rc" = 0 ] || { vhh_fail "REFITT_TEST_PG=1: exit $vhh_rc: $(tail -n 3 "$vhh_out/scratch.err" | tr '\n' ' ')"; }
[ "$(docker inspect -f '{{.State.Running}}' "$scratch")" = true ] || vhh_fail "REFITT_TEST_PG=1: the helper stopped the scratch database"
docker rm -f -v "$scratch" >/dev/null
trap - EXIT INT TERM
[ "$(vhh_get "$j" database.port)" = "$sport" ] && [ "$(vhh_get "$j" users)" -gt 0 ] 2>/dev/null \
    || vhh_fail "REFITT_TEST_PG=1: the command did not use the seeded scratch database"
vhh_check_isolated "$j" "R2 scratch"
vhh_check_rootkey "$j" "R3 scratch"
vhh_stdout_is "$vhh_out/scratch.out" cmd-out || vhh_fail "R6 scratch: stdout is not exactly the command's"
vhh_check_cwd "$j" "R7 scratch"
[ "$(vhh_get "$j" session_timezone)" = "$zone" ] || vhh_fail "R10 scratch: libpq session zone is $(vhh_get "$j" session_timezone)"
[ "$(vhh_get "$j" server_answered)" = true ] || vhh_fail "scratch: the dev server did not answer the command"
check_torn_down scratch
vhh_ok "REFITT_TEST_PG=1: scratch database seeded and used, isolated, own rootkey, zone $zone, torn down, scratch left running"

vhh_check_tree "R7/R11"
vhh_ok "R7/R11 worktree byte-identical (stale uv.lock included); developer home untouched"
printf 'PASS container_drive\n'
