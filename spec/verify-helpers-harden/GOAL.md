# GOAL — Harden the throwaway-environment helpers

> **Origin spec.** The *what* and *why* — the locked contract `code-review` grades against.
> The *how* lives in [`PLAN.md`](PLAN.md) and [`TECH.md`](TECH.md) (written by `code-plan`).
> Keep this at the right altitude: solved and bounded, but not over-specified — leave design
> freedom for the plan. Edit requirements here; do **not** silently drift them during build.

- **slug:** verify-helpers-harden
- **kind:** test
- **appetite:** small

## Problem

`tools/temp_db.sh` (the fast SQLite tier) and `tools/temp_pg.sh` (the faithful Postgres tier) are
the substrate every cycle verifies on: the profile's `verify` and the release `gate` both run
through `temp_pg.sh` (`AGENTS.md` § Factory → Profile, Release recipe). `AGENTS.md` § Factory →
Throwaway environment sets a seven-item contract for them and says plainly that both fall short of
it. The test-suite cycle (`issues/test-suite-repair.md`) cannot start until they meet it. Every
defect below is **pre-existing**: both scripts arrived unchanged in `aa7623d`, when they moved out
of the retired `.agents/` tree.

Evidence, re-checked against `origin/develop` at `aa7623d`:

- **`temp_db.sh` cannot run unattended.** It runs `refitt database init` (`temp_db.sh:43`), and
  `init` asks for confirmation on every SQLite database
  (`py/apps/refitt-admin/src/refitt/admin/database/init.py:75-78`). The guard tests
  `'host' in db_cfg`, but `DatabaseConfiguration` always carries a `host` key, `None` on SQLite
  (`py/libs/refitt-data/src/refitt/database/core.py:63`). With no TTY, the prompt blocks or fails.
- **A developer's config leaks into both helpers.** The helpers force a few `REFITT_DATABASE_*`
  variables but leave `HOME` alone. Configuration merges the system, user (`$HOME/.refitt/config.toml`)
  and local (`$CWD/.refitt/config.toml`) files under the environment
  (`py/libs/refitt-core/src/refitt/core/config.py:142-150`, paths from
  `py/libs/refitt-core/src/refitt/core/platform.py:19-38`). So any key the helper does not force
  survives from the user file. A user `database.default` that sets `database`, `user`, `password`,
  `host` or `port` then fails SQLite validation against the forced `file`
  (`core.py:100-104`; the seed cited `100-101`, which covers only the `database` case). A
  `rootkey_eval` key in the user config collides with an environment `rootkey`, and an environment
  layer cannot override `*_eval`/`*_env` keys (`issues/test-suite-repair.md` Notes). Importing
  `refitt.core.platform` creates `~/.refitt/{lib,run,log}` in the real home (`platform.py:42-46`).
- **`temp_pg.sh` keeps no state directory.** It creates none, does not change directory, and
  writes app state wherever the real `HOME` and the caller's cwd point (contract items 2–4).
- **`temp_pg.sh` can reach a real database.** In container mode it still takes host, port,
  database, user and password from any inherited `REFITT_DATABASE_DEFAULT_*` variable
  (`temp_pg.sh:22-26`), then runs `init --drop` against them (`temp_pg.sh:66`). A developer who
  exports those variables for their own database gets it dropped.
- **`temp_pg.sh` bring-up is fragile.** It publishes a fixed port `5544` on every interface
  (`temp_pg.sh:26,46`), so two runs collide. It waits on `pg_isready` inside the container
  (`temp_pg.sh:48`), not on a connection from the host. It starts the dev server and sleeps a fixed
  5 s (`temp_pg.sh:73-75`). It checks that a `docker` binary exists (`temp_pg.sh:39`) but not
  that a daemon answers.
- **The rootkey is conditional and inheritable.** `temp_pg.sh:70` exports a rootkey only with
  `REFITT_TEMP_WITH_SERVER=1`, and prefers any inherited `REFITT_API_ROOTKEY` over a fresh one.
  `temp_db.sh` exports none.
- **No session timezone.** Seed data and expected values carry literal `-04:00` offsets. CI sets
  `TZ: America/Indianapolis` for the runner only (`.github/workflows/tests.yml:48`), which libpq
  ignores, and the `postgres` image rejects that legacy zone name; the canonical IANA name is
  `America/Indiana/Indianapolis` (`issues/test-suite-repair.md` Notes).
- **A verify can rewrite the lock.** Both helpers call plain `uv run` (`temp_db.sh:43`,
  `temp_pg.sh:66,70,73`). The committed `uv.lock` is stale (`issues/workspace-install-hygiene.md`),
  so any `uv run` re-locks it and dirties the worktree. Shaping found `uv.lock` already modified in
  this cycle's fresh worktree, with no step having edited it on purpose.
- **Working directory against the documented paths.** `temp_db.sh:38` runs the command inside the
  state directory, as contract item 4 asks. That breaks its own documented usage
  (`tools/temp_db.sh sh -c "uv run pytest -m unit tests/test_database"`, `temp_db.sh:6`), whose
  relative path no longer resolves. `temp_pg.sh` stays in the caller's cwd, which keeps the
  profile's `verify` (`tools/temp_pg.sh uv run pytest -v`) working but breaks item 4.

## Outcome / vision

On a developer machine with a populated `~/.refitt`, a stale lock and no terminal, either helper
runs any command against a fresh throwaway REFITT instance and leaves nothing behind. The developer's
config, keys and databases are never read or touched. The worktree is unchanged afterwards. The
command's exit status comes back unchanged. The test-suite cycle can then take `temp_pg.sh` as its
verify and trust what it reports.

## Acceptance criteria (the contract)

"Either helper" means `tools/temp_db.sh` and `tools/temp_pg.sh` in each bring-up mode they support:
the `temp_pg.sh` container mode, and its `REFITT_TEST_PG=1` mode against a scratch database.
"A populated home" means a real `$HOME/.refitt/config.toml` whose `database.default` sets
`database`, `host`, `user`, `password` and `port`, and whose `api` section sets `rootkey_eval`.

- **R1** — WHEN `tools/temp_db.sh <cmd>` runs with stdin not a terminal, it SHALL create and seed
  the throwaway database and run `<cmd>` without prompting.
- **R2** — WHILE a populated home exists, and a `.refitt/config.toml` sits at the repo root, WHEN
  either helper runs `<cmd>`, `<cmd>` SHALL see only the throwaway configuration: no value from
  the developer's system, user or local config files. Nothing under the developer's
  `$HOME/.refitt` SHALL be created, modified or deleted.
- **R3** — WHEN either helper runs `<cmd>`, `<cmd>` SHALL see a REFITT API rootkey generated for
  that run, whether or not `REFITT_TEMP_WITH_SERVER=1` is set, and never a key inherited from the
  developer's config or environment.
- **R4** — WHEN `tools/temp_pg.sh` runs in container mode, the database it seeds and `<cmd>` uses
  SHALL be the container it started, whatever `REFITT_DATABASE_*` variables the caller exported.
- **R5** — WHEN either helper exits by any path (the command succeeds, the command fails, the
  bring-up or seed fails, or the helper receives INT or TERM), its state directory SHALL be gone,
  and for `temp_pg.sh` so SHALL the container and the dev server it started.
- **R6** — WHEN either helper runs `<cmd>`, the helper's own output SHALL go to stderr only, and
  its exit status SHALL equal `<cmd>`'s.
- **R7** — WHEN either helper runs `<cmd>`, `<cmd>`'s working directory SHALL be the helper's
  state directory (contract item 4), and `<cmd>` SHALL find the repo root in an environment
  variable the helper exports. The profile's `verify`, the release recipe's `gate` and each helper's
  usage lines SHALL use root-anchored paths and find their tests. After any of those invocations,
  the worktree SHALL hold no new untracked or modified file, including pytest's cache and any other
  tool output.
- **R8** — WHEN `tools/temp_pg.sh` starts a container, it SHALL publish Postgres only on
  `127.0.0.1`, on a port free at that moment, so two concurrent runs both succeed. It SHALL run
  `<cmd>` only after a connection from the host succeeds and, with `REFITT_TEMP_WITH_SERVER=1`,
  after the dev server answers an HTTP request. IF either is not ready within a bounded wait,
  THEN it SHALL exit non-zero with a stderr message naming which.
- **R9** — IF `tools/temp_pg.sh` runs in container mode and no Docker daemon answers, THEN it SHALL
  exit non-zero before starting anything, with a stderr message that names `REFITT_TEST_PG=1` as
  the alternative.
- **R10** — WHEN `tools/temp_pg.sh` runs `<cmd>`, every Postgres session `<cmd>` opens SHALL use
  the zone the seed data assumes, by its canonical IANA name, whatever the host's `TZ`.
- **R11** — WHEN either helper runs on a worktree whose `uv.lock` is out of date, `uv.lock` and every
  other tracked file SHALL be byte-identical afterwards.
- **R12** — WHEN the cycle lands, each helper's header comments and `AGENTS.md` § Factory →
  Throwaway environment SHALL describe the helpers as they then behave, with no caveat or
  "falls short" note pointing at this seed.

## Non-goals (no-gos)

- **The test suite.** Re-homing, codemods, markers, `testpaths` and the seed-data timezone strings
  belong to `issues/test-suite-repair.md`. This cycle needs only enough of a drive to prove the
  helpers; a failing or non-collecting suite is not this cycle's defect.
- **CI.** `.github/workflows/` is untouched, including the runner-only `TZ` in `tests.yml:48`.
- **REFITT product code.** No change under `py/`. In particular, the always-on SQLite prompt in
  `refitt.admin`'s `database init` (`init.py:75-78`) is a product defect; R1 is met on the helper
  side, and fixing `init` itself is a separate seed, which the plan step files under `issues/`:
  [`issues/init-sqlite-prompt.md`](../../issues/init-sqlite-prompt.md).
- **The stale lock.** Regenerating `uv.lock` and the workspace's undeclared dependencies belong to
  `issues/workspace-install-hygiene.md`. R11 requires only that a helper never rewrites the lock.
- **The tier split.** Which drives belong on SQLite versus Postgres is
  `issues/db-dialect-parity.md`.
- **A Docker-free Postgres bring-up**, such as a local `initdb` in the state directory.
- **Inherited `REFITT_*` variables beyond the database and the rootkey.** R4 and R3 cover the two
  that reach real data or keys. Scrubbing every other inherited `REFITT_*` variable is not
  proposed; the helpers' documented inputs (`REFITT_TEST_PG`, `REFITT_TEST_PG_IMAGE`,
  `REFITT_TEMP_WITH_SERVER`, `REFITT_TEMP_DB_INIT`, `REFITT_LOGGING_LEVEL`) stay as they are.
- **The remote-database confirmation in `REFITT_TEST_PG=1` mode.** When a scratch database is on a
  non-local host, `init` still asks before dropping it; R1 binds only `temp_db.sh`.

## Clarifications

- **Q:** R7 — contract item 4 and the documented invocations contradict each other today. Where
  should `<cmd>` run? — **A:** In the state directory, per item 4 as written. Each helper exports
  the repo root to `<cmd>`. The profile's `verify`, the release recipe's `gate` and each helper's
  usage lines change to root-anchored paths in this cycle. Pytest's cache and other tool output
  must not land in the worktree. The plan picks the mechanism (resolved 2026-11-09).
- **Q:** How is `temp_pg.sh` verified when the build host has no Docker? The shaping host has
  neither Docker nor any Postgres binary, so R4, R5, R8 and R10 cannot run there in container
  mode. — **A:** The build verifies `temp_db.sh` and `temp_pg.sh`'s no-daemon path (R9) locally.
  Before review, the foreman has the container-mode drive run on a Docker-capable host. The plan
  names that drive as one command. Falling back to checking container mode only by reading the
  script needs the maintainer's word, recorded here as a later Clarification (resolved 2026-11-09).
- **Q:** Twelve R-IDs exceed the size circuit-breaker. Split? — **A:** No; accepted as one
  deliverable (resolved 2026-11-09).
- **Q:** Does the SQLite `init` prompt get its own seed? — **A:** Yes. The plan step files it; it
  stays a non-goal here (resolved 2026-11-09).
- **Q:** Do the two scope non-goals stand: other inherited `REFITT_*` variables, and the
  remote-database confirmation in `REFITT_TEST_PG=1` mode? — **A:** Yes, both as written (resolved
  2026-11-09).

## Related materials

- Seed: [`issues/verify-helpers-harden.md`](../../issues/verify-helpers-harden.md)
  (`status: unshaped` at promotion)
- Roadmap: `ROADMAP.md` → "The verify helpers are not hermetic"
- Contract: `AGENTS.md` § Factory → Profile (`verify`, `throwaway environment`), Release recipe
  (`gate`), Throwaway environment
- Sources: `tools/temp_db.sh`, `tools/temp_pg.sh`;
  `py/apps/refitt-admin/src/refitt/admin/database/init.py`;
  `py/libs/refitt-data/src/refitt/database/core.py`;
  `py/libs/refitt-core/src/refitt/core/{config,platform}.py`; `.github/workflows/tests.yml`
- Depends on this: [`issues/test-suite-repair.md`](../../issues/test-suite-repair.md) (its Notes
  carry the rootkey, `HOME` and timezone evidence)
- Neighbours: [`issues/workspace-install-hygiene.md`](../../issues/workspace-install-hygiene.md),
  [`issues/db-dialect-parity.md`](../../issues/db-dialect-parity.md)
