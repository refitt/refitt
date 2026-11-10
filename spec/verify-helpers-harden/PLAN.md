# PLAN — Harden the throwaway-environment helpers

> **Status:** Draft for review · **Last updated:** 2026-11-10
> **Authoritative technical design.** The *how*. Vision/contract is [`GOAL.md`](GOAL.md);
> the phased executable roadmap is [`TECH.md`](TECH.md). There is no `research/`: this is the lean
> path (`appetite: small`), and the probes that changed the design are recorded in §4. Every design
> element traces to a GOAL R-ID.

## 1. Summary

Both helpers move their shared plumbing into a sourced `tools/temp_common.sh`: refuse unsafe hosts
before creating anything, make one state directory the command's cwd, `HOME` and `TMPDIR`, scrub
inherited database and rootkey variables, run `uv` with `UV_NO_SYNC`, export a fresh rootkey and the
repo root, run the command in its own process group, and tear everything down from one EXIT trap.
`temp_db.sh` adds the SQLite seed (answering `init`'s spurious prompt itself). `temp_pg.sh` adds a
daemon check, a container published on `127.0.0.1` at a Docker-picked port, a host-side readiness
probe, a fixed session zone, and a dev server on a free port with an HTTP readiness probe. The
profile's `verify` and the release `gate` change to `"$REPO_ROOT"`-anchored pytest, and § Factory →
Throwaway environment is rewritten. Three phases; container mode is proven by one drive on a Docker
host before review.

## 2. Design

### `tools/temp_common.sh` (new, sourced, POSIX `sh`)

Sourced by both helpers after they set `temp_name` and `temp_kind`. It defines:

- **`REPO_ROOT`** — the parent of the helper's own directory (`cd "$(dirname "$0")/.." && pwd -P`),
  so the helper works from any cwd. Contract item 1 is met by anchoring, not by assuming the caller's
  cwd (R7).
- **`temp_preflight`** — runs before anything is created, and stops with a stderr message when a
  run cannot be hermetic:
  - as root (REFITT's `platform.py` then uses `/var/lib/refitt`, outside any state directory);
  - when `/etc/refitt.toml` exists (`config.py` reads the system file whatever `HOME` says; R2);
  - when the project environment (`$UV_PROJECT_ENVIRONMENT`, else `$REPO_ROOT/.venv`) has no
    `pyvenv.cfg`: with `UV_NO_SYNC`, `uv run` would otherwise create an empty `.venv` inside the
    worktree (R7, R11);
  - when `perl` is missing (the process-group wrapper below).
- **`temp_enter`** — in this order:
  1. pins `UV_CACHE_DIR` to the caller's value, or to `uv cache dir`, before `HOME` moves;
  2. `mktemp -d "${TMPDIR:-/tmp}/refitt-temp-$kind.XXXXXX"` plus `tmp/` inside it;
  3. unsets every inherited `REFITT_DATABASE_*`, `REFITT_API_ROOTKEY*` and libpq `PG*` variable
     (an inherited `REFITT_API_ROOTKEY_EVAL` expands to `api.rootkey.eval` and clobbers the key;
     an inherited `PGHOSTADDR` overrides any host libpq is given; see §4);
  4. exports `REPO_ROOT`, `HOME=$state`, `TMPDIR=$state/tmp`, `UV_PROJECT=$REPO_ROOT`,
     `UV_NO_SYNC=1`, `PYTHONPYCACHEPREFIX=$state/pycache`, appends
     `-o 'cache_dir=$state/pytest-cache'` to `PYTEST_ADDOPTS`, forces
     `REFITT_DATABASE_SCOPE_{READ,WRITE}=default`, and defaults `REFITT_LOGGING_LEVEL=warning`;
  5. `cd "$state"`.

  With `HOME` and cwd both in the state directory, REFITT's user and local config paths
  (`platform.py:29-38`) both resolve to `$state/.refitt/config.toml`, which never exists, and
  `~/.refitt/{lib,run,log}` (`platform.py:42-46`) and astropy's `~/.astropy` land in the state
  directory (R2).
- **`temp_rootkey`** — exports `REFITT_API_ROOTKEY` from `Cipher.new_rootkey()` (the same call CI
  uses), after the scrub and the database variables, so the import sees only throwaway config (R3).
- **`temp_run "$@"`** — with stdin not a terminal, starts the command in the background through
  `perl -e 'setpgrp; exec'` (its own process group, INT and QUIT reset to default) with the caller's
  stdin carried on fd 3 past the shell's `/dev/null` default for background jobs, then `wait`s and
  records its status. At a terminal it runs in the foreground instead, so the command can read the
  terminal and Ctrl-C reaches it directly (R5, R6).
- **Traps.** EXIT runs `temp_cleanup`: ignore further INT and TERM (`trap '' INT TERM`, so a
  second Ctrl-C cannot cut the teardown short), `set +e`, stop the command's group and the
  server's group (`temp_stop_group`: TERM the group, `wait` the leader, KILL the group; a background
  watchdog KILLs after 10 s if the leader ignores TERM), `docker rm -f -v` the container (anonymous
  volumes too) with the caller's `HOME`, `cd /`, `chmod -R u+w` then `rm -rf` the state directory
  (pytest leaves read-only directories under `TMPDIR`), and exit with the status it was entered
  with. INT and TERM ignore themselves, stop the command's group and exit 130 / 143, which runs
  EXIT (R5).
- **`temp_docker`** — every `docker` call runs with the caller's `HOME`, so Docker contexts and
  credentials still resolve after `HOME` moves.

Every message goes to stderr through `temp_say`/`temp_die`; every child the helper runs for itself
(`init`, the server, docker) has stdout sent to stderr or `/dev/null` (R6).

### `tools/temp_db.sh`

`temp_preflight`, `temp_enter`, force `REFITT_DATABASE_DEFAULT_PROVIDER=sqlite` and
`_FILE=$state/refitt.db`, `temp_rootkey`, then
`printf 'y\n' | uv run refitt database init ${REFITT_TEMP_DB_INIT:---test} >&2` (R1; see deviation
row 1), then `temp_run "$@"` and `exit "$temp_status"`. Usage line becomes
`tools/temp_db.sh sh -c 'uv run pytest -m unit "$REPO_ROOT/tests/test_database"'` (R7).

### `tools/temp_pg.sh`

1. **Mode and daemon check, before anything is created** (R9). Container mode (the default):
   `command -v docker && docker info` (with the caller's `HOME`, under a 10 s `perl` alarm so a
   wedged or starting daemon cannot hang it), else stop with a message naming `REFITT_TEST_PG=1`
   and the five `REFITT_DATABASE_DEFAULT_*` variables. `REFITT_TEST_PG=1`: capture the caller's five
   `REFITT_DATABASE_DEFAULT_{HOST,PORT,DATABASE,USER,PASSWORD}` (defaults `127.0.0.1`, `5432`,
   `refitt_test`, `refitt`, `refitt`) before the scrub drops them.
2. `temp_preflight`, `temp_enter`, `export PGTZ=America/Indiana/Indianapolis` (R10).
3. **Container** (R4, R8, R10): name `refitt-temp-pg-<state suffix>`, label
   `refitt.temp-pg.state=$state`, fixed throwaway credentials (database `refitt_test`, user and
   password `refitt`; inherited values were already scrubbed, so R4 holds by construction),
   `-e TZ=America/Indiana/Indianapolis` (initdb takes the server's default `timezone` from `TZ`, so
   non-libpq sessions get the zone too), `-p 127.0.0.1::5432` (Docker picks a free host port at that
   moment), image `${REFITT_TEST_PG_IMAGE:-postgres:16}`. The host port comes from
   `docker port <ctr> 5432/tcp`.
4. **Readiness** (R8): loop until a psycopg2 connection from the host succeeds
   (`PG*` variables, `PGCONNECT_TIMEOUT=2`, through `uv run python`), failing fast if
   `docker inspect` says the container stopped, and otherwise at a wall-clock deadline of 60 s with
   `Postgres did not accept a connection from the host within 60s`. Not `pg_isready` in the
   container: the image's first server listens only on its socket, and Docker's proxy accepts TCP
   before Postgres does.
5. Force `REFITT_DATABASE_DEFAULT_*` to the container's (or the captured scratch) values,
   `temp_rootkey`, then `uv run refitt database init --drop --test >&2` (stdin `/dev/null` in
   container mode; inherited in `REFITT_TEST_PG=1` mode, where a remote host still asks, a GOAL
   non-goal).
6. **Dev server** with `REFITT_TEMP_WITH_SERVER=1` (R8): pick a free port by binding
   `127.0.0.1:0`, export `REFITT_API_SITE=http://localhost` and `REFITT_API_PORT`, start
   `uv run refitt-server start --dev --port <p>` in its own process group (the werkzeug reloader
   forks a child that a single-pid kill would orphan), stdout to stderr, then poll
   `http://127.0.0.1:<p>/` with proxies disabled (a proxy's error page is an HTTP response too)
   until any HTTP response, to a 30 s wall-clock deadline with
   `the dev server did not answer HTTP within 30s`.
7. `temp_run "$@"`; `exit "$temp_status"`.

### `AGENTS.md`

- Profile `verify`: `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest -v "$REPO_ROOT"' && make client-boundary metadata`.
- Release recipe `gate`: `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest -v "$REPO_ROOT"'`.
  Pytest given the root as its argument picks the same rootdir and `pyproject.toml` ini as before,
  and collects the same tree (dot-directories such as `.venv` and `.worktrees` are skipped by
  pytest's `norecursedirs`).
- § Factory → Throwaway environment: the seven-item contract stays; the prose after it is rewritten
  to state the behaviour above, and the "Both fall short" paragraph goes (R12).

### Requirement → design map

| R-ID | Design element(s) that satisfy it |
|------|-----------------------------------|
| R1 | `temp_db.sh` pipes `y` into `init` and sends its stdout to stderr; nothing reads the caller's stdin before the command |
| R2 | `HOME` and cwd in the state directory (user and local config paths point there); preflight refuses `/etc/refitt.toml` and root; scrub of `REFITT_DATABASE_*` |
| R3 | scrub of `REFITT_API_ROOTKEY*`; `temp_rootkey` in both helpers, unconditionally |
| R4 | container mode never reads inherited database or libpq variables: scrubbed, then forced to the container's |
| R5 | one EXIT trap: command group, server group, `docker rm -f -v`, `rm -rf` state; INT/TERM handlers stop the command's group first |
| R6 | `temp_say`/`temp_die` and every helper-run child to stderr; `exit "$temp_status"` from `wait` |
| R7 | cwd = state directory; `REPO_ROOT` exported; pytest cache and bytecode redirected into the state directory; root-anchored `verify`, `gate` and usage lines; preflight refuses a missing environment |
| R8 | `-p 127.0.0.1::5432`; host-side psycopg2 probe; server on a free port with HTTP probe; wall-clock deadlines with named messages |
| R9 | `docker info` (caller's `HOME`, 10 s bound) before `mktemp`; message names `REFITT_TEST_PG=1` |
| R10 | `PGTZ` exported in both modes; container `TZ` sets the server default |
| R11 | `UV_NO_SYNC=1` and `UV_PROJECT` for every `uv run`, the command's included; no `uv sync`/`uv lock` anywhere |
| R12 | both helper headers rewritten; § Throwaway environment rewritten without the caveat |

## 3. Invariant gate (AGENTS.md constitution check)

Walked before the design and again against it. The change touches no product code and no path on
the high-blast-radius list; the sections it touches:

- **§4 import-time determinism** — unchanged: the helpers only set environment variables before
  REFITT imports, which is how REFITT is configured today. `HOME` moving changes where
  `platform.py` creates its directories, never when.
- **§5 auth posture** — the rootkey stays a Fernet key from `Cipher.new_rootkey()`; nothing echoes
  it (stdout carries only the command's output).
- **§8 private-file permissions** — no config file is written; the check is untouched.
- **§C4 dialect coupling** — `temp_db.sh` stays SQLite-only and says so; `temp_pg.sh` stays the
  Postgres tier.
- **§K2 test provisioning** — both helpers still seed with `refitt database init --test`.
- **§K4 declarative comments** — helper comments state why, and carry no R/P ids.
- **§K6 same-commit docs** — the helpers are not REFITT's CLI or public API, so no Sphinx change;
  the documents that restate the helpers (their headers, § Factory) change in the same phase as the
  behaviour they describe.
- **§ Factory** — the profile `verify`, release `gate` and Throwaway environment change (row 2).

### Deviation justifications

| Deviation | Why needed | Simpler alternative rejected because |
|-----------|-----------|--------------------------------------|
| 1. **Reading of R1, "without prompting".** `temp_db.sh` pipes `y` into `refitt database init`; `init` still calls `input()` and prints its prompt line, which the helper sends to stderr. | `init` asks on every SQLite database (a product defect, now `issues/init-sqlite-prompt.md`), and the GOAL puts `py/` out of scope with "R1 is met on the helper side". Nobody is asked and nothing waits on a terminal. | Calling `create_all`/`load_defaults` from Python instead of the CLI avoids the prompt line entirely, but stops exercising `refitt database init`, which §K2 and § Factory name as the way a test database is provisioned. If the sign-off reads R1 as "no prompt is issued at all", this row flips to that alternative. |
| 2. **§ Factory edited inside a `[test]` cycle.** Phase commits change the profile `verify`, the release `gate` and § Throwaway environment. | R7 and R12 require these edits, and Q1 places them in this cycle; the helpers' cwd change would break the old `verify` line, so they must land in the same commit (§K6's spirit, "a rule restated in N places"). | A separate `[harness]` commit or PR leaves the cycle's branch with a `verify` that no longer runs between the two. The human gate a `[harness]` change needs is this PLAN/TECH sign-off and the review. |
| 3. **Two refusals the GOAL does not ask for**: as root, and with `/etc/refitt.toml` present. | R2 names the system config file; REFITT reads `/etc/refitt.toml` whatever `HOME` says, and as root it keeps state in `/var/lib/refitt`. No helper-side setting can redirect either without product change. Refusing is the only way the command never sees a system value. | Ignoring them meets R2 only on hosts without the file. Neither refusal is reachable on the build host (not root, no file), so both are graded by reading and by the review. |
| 4. **Reading of R7's "after any of those invocations".** The worktree check covers the helper invocations in `verify`, `gate` and the usage lines, not the rest of those lines. | The `verify` line continues `&& make client-boundary metadata`, which writes `dist/` and `.venv-client/` by design (`clean_paths`); the release `gate` starts with `uv sync --all-packages`, which re-locks while the lock is stale. R7's trigger is "WHEN either helper runs `<cmd>`". | Holding the whole line to "no new file" means changing the Makefile targets and the release recipe's `uv sync`, outside this GOAL (`workspace-install-hygiene` owns the lock). |
| 5. **A third file, `tools/temp_common.sh`.** | The scrub, isolation, process-group runner and teardown are identical in both helpers; one copy keeps them from drifting. | Duplicating ~90 lines in both scripts doubles the surface the gates and the review must cover. |

Each row was read against the wording of every R-ID it touches (R1, R2, R7, R12): none changes what
an R-ID requires, and rows 1 and 4 are flagged for the sign-off as readings.

## 4. Rabbit holes (resolved)

Settled by probes on the build host (macOS arm64, no Docker, no Postgres, no libpq, no librdkafka),
in throwaway copies of the tree outside the repo.

- **`uv run --frozen` cannot work here.** The committed lock lacks the `refitt-host` member, so
  `--frozen` refuses it (`Missing workspace member`). `UV_NO_SYNC=1` runs against the existing
  environment and leaves `uv.lock` byte-identical, even with `UV_PROJECT` pointing elsewhere.
- **`UV_NO_SYNC` with no environment creates one.** `uv run --no-sync` on a tree without `.venv`
  creates an empty `.venv` (this is how the cycle worktree got an empty Python 3.15 one). Hence the
  preflight.
- **The re-lock breaks `init`.** An unfrozen sync re-resolves numpy to 2.5, and astropy 7.0.1 then
  fails on `np.in1d` during `refitt database init`. With numpy pinned back to the lock's 2.2.4, the
  seed runs. The gates build their environment that way (`verify/lib.sh`), never in the worktree.
- **Native libraries.** None installed; `psycopg2` 2.9.10 is source-only on PyPI here. The gate
  environment installs `psycopg2-binary` at the lock's version and skips `confluent-kafka` (only
  `refitt-broker` imports it). The SQLite tier never imports psycopg2.
- **`REFITT_API_ROOTKEY_EVAL` in the environment** expands to `api.rootkey.eval`, replacing the key
  with a namespace: the scrub must cover `REFITT_API_ROOTKEY*`, not just the key.
- **Background jobs and stdin.** `dash` (Debian's `/bin/sh`) gives a background job `/dev/null` for
  stdin even with `<&0`, and has no job control without a terminal (`set -m` is refused). Carrying
  stdin on fd 3 and `perl -e 'setpgrp; exec'` work in both `dash` and macOS `sh` (probed). `setsid`
  is absent on macOS.
- **Signals ignored on entry cannot be trapped.** A shell started in the background by a
  non-interactive shell ignores INT, and then cannot trap it; the INT checks start the helper
  through a wrapper that resets INT to default. The command's group gets TERM, not INT.
- **Docker after `HOME` moves.** Docker Desktop's CLI finds its context under `~/.docker`; every
  docker call keeps the caller's `HOME`.
- **Anonymous volumes.** `postgres` declares a volume; `docker rm -f` without `-v` leaves one per
  run.
- **Bounded waits.** Counting one-second iterations overstates nothing but understates wall time
  (each probe can take 2 s); both waits use `date +%s` deadlines, so the 60 s and 30 s in their
  messages are wall-clock.
- **No `ps`/`pgrep` in the agent sandbox.** Gates check processes by recorded pid with `kill -0`.

**Adversarial design review** (trigger 3; the deliverable is the verify substrate). One fresh
reviewer pass, given the GOAL, this design, the drafted gates and the prototype, ran four mutants
in a throwaway copy. It found 21 items; all were folded before commit:

- *False greens, now closed.* R3 in `temp_pg.sh` was only checked with the server on (a mutant
  that kept the old server-only rootkey passed): the local gate adds a no-server run and the drive's
  second concurrent run has no server. Usage lines were checked only in the `sh -c` form (an added
  unanchored line passed): every example line is now checked for `sh -c` and `"$REPO_ROOT"`-anchored
  test paths. The drive saw only labelled containers: it now compares every container and volume on
  the daemon. Stdout checks dropped trailing newlines: they compare bytes.
- *False reds and weak checks, now fixed.* The gates resolve `UV_CACHE_DIR` while `HOME` is real
  (else uv wrote into the populated home). The no-docker case links every command but docker
  instead of trimming PATH directories (Linux keeps docker in `/usr/bin`). The drive's seed-failure
  case broke config before the seed; a `uv` shim now fails only `init`, and the local gate stubs an
  `init` failure. "Finds its tests" no longer counts collection errors. The profile's `verify` line
  is now run (collection only) locally in stubbed mode and in the drive. Timeouts send TERM, not
  SIGALRM, so the helper still tears down. The missing-environment refusal has a check.
- *Prototype defects, now designed out and checked.* A second INT/TERM during teardown killed it
  (`trap ''`; TERM sent twice). The server probe went through `http_proxy` (proxies disabled;
  checked against a 502 proxy). `docker info` was unbounded (10 s alarm; checked with a wedged fake
  daemon). A read-only leftover made `rm -rf` fail under `set -e` (checked). Inherited `PG*`
  variables reached libpq (scrubbed; inherited in every gate run). The manifest opened FIFOs; pid
  checks retry for zombies; the drive removes its scratch container on any exit; the
  Throwaway-environment text no longer claims uv's cache moves.

Re-run after the fold: the reviewer's M1 and M2 now fail their gates
(`R3 (stubbed, no server)`, `R7: usage line does not use sh -c`).

## 5. Risks & open questions

- **Container mode is unverified until the drive runs.** No local phase claims R4, R8, R10 or the
  container-mode half of any R-ID. The foreman runs, on a Docker host, from the branch tip:

  ```
  sh spec/verify-helpers-harden/verify/container_drive.sh
  ```

  It needs Docker, `uv`, `perl`, `git` and network to PyPI and Docker Hub, and ends
  `PASS container_drive`. It was written without a Docker host to dry-run it on, so its first run
  may find drive bugs as well as helper bugs; a drive fix is a `spec/` change, not a helper change.
- **TERM at a terminal is deferred.** With a terminal on stdin the command runs in the foreground,
  so a TERM sent to the helper alone acts when the command exits; the cleanup still runs then.
  Ctrl-C reaches the whole foreground group at once. Unattended runs (every gate and verify) use
  the process-group path.
- **The drive needs the daemon to itself.** Its leak check compares every container and volume
  before and after; another workload starting containers meanwhile reads as a leak (a false red,
  never a false green).
- **The dev-server port is picked, then bound.** Another process can take it in between; the
  server would then fail and the 30 s wait reports it. Postgres has no such window (Docker picks).
- **`perl` becomes a requirement** of both helpers (present on macOS and in Debian's essential set).
- **`/etc/refitt.toml` and root refusals** are unreachable on the build host; graded by reading.
- **Usage lines and the suite.** The SQLite usage line collects 240 tests and errors on one module
  today (`-m unit` deselects them all); "finds its tests" is graded as pytest reporting at least one
  test found, not as passing. A red suite is `test-suite-repair`'s.

## 6. Verification strategy

Every gate drives the real helpers from a fixture exported from the index (`git checkout-index`) to
a lab under `$TMPDIR`, never from the worktree, with: a populated developer home (`HOME` pointed at
a lab directory whose `.refitt/config.toml`, mode 0600, sets `database.default` `database`, `host`,
`user`, `password`, `port` and `api.rootkey_eval`); a repo-root `.refitt/config.toml`; inherited
`REFITT_DATABASE_DEFAULT_*`, `REFITT_API_ROOTKEY` and `REFITT_API_ROOTKEY_EVAL`; stdin from
`/dev/null`; a per-run empty `TMPDIR` (empty afterwards means the state directory is gone); and the
committed stale `uv.lock` (precondition: `uv lock --check --offline` says it needs updating). The
command is `verify/config_probe.py`, which records what it sees as JSON. A tree manifest (every
entry, mode and content hash) of the fixture and of the developer home is compared before and
after all runs.

| Gate | Phase | Proves |
|---|---|---|
| `verify/gate_temp_db.sh` | P1 | R1, R2, R3, R5 (success, command fails, seed fails, read-only leftovers, TERM, INT, TERM twice), R6, R7 (cwd, `REPO_ROOT`, missing-environment refusal, every header example in `sh -c` form, anchored, finding tests), R11, stdin passthrough |
| `verify/gate_temp_pg_local.sh` | P2 | R9 (no docker; a daemon that fails `info`, with only `info` called; a daemon that hangs). Supporting only: `REFITT_TEST_PG=1` mode with `init` and the dev server stubbed, for config isolation, rootkey with and without the server, stdout, cwd, PGTZ export, seed failure, the profile's `verify` line collecting tests, server readiness before the command, server teardown on exit and TERM, the 30 s server timeout behind a 502 proxy, anchored usage lines, R11 |
| `verify/gate_docs.sh` | P3 | R12 (no caveat; key facts in both headers and the section), R7 (`verify` and `gate` anchored; the recipe still parses), scope since the plan commit (no `py/`, `.github/`, `uv.lock`), no private paths in added lines, the deferral ledger. Modes `all` (default), `phase`, `pre-push` |
| `verify/container_drive.sh` | before review | R4, R5 (incl. every container and volume), R8, R10 and container-mode R2, R3 (with and without the server), R6, R7 (usage lines and the profile's `verify` line), R11; `REFITT_TEST_PG=1` mode against a real scratch Postgres |

Every inherited-variable run also carries `PGHOSTADDR` and `PGDATABASE` markers. Gate runs are
sequential except the drive's one concurrency check, and each run is bounded (TERM after 300 s,
600 s for the drive's usage lines).

Dry runs at planning, on a prototype worktree cut to each phase, after the review fold:
`gate_temp_db.sh` passes on the P1 tree (73 s warm, 10 s of it the TERM-twice watchdog) and fails
on the base helpers; `gate_temp_pg_local.sh` passes on the P2 tree (112 s, about 50 s of it the
server and daemon timeouts) and fails on the base `temp_pg.sh` (it calls `docker run` past a dead
daemon); `gate_docs.sh` passes `phase` and `pre-push` (under 1 s) and `all` (3 min 21 s) on the final tree. The
container drive could not be dry-run.

---

*Backing research: none (lean path); probes are summarized in §4.*
