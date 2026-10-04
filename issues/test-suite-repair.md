---
status: unshaped
kind: test
appetite: big
lane: public
---

# Repair and re-home the test suite

## Problem

The suite cannot collect. 16 test files import the pre-split module tree, which was removed by
`ef42554` ("Major project refactor", 2025-03-19). The root tests were last touched in `a80eab5`
(2024-06-12). On the pre-#24 CI run (`8422947`, lock intact) pytest got as far as collection:
```
collecting ... collected 354 items / 16 errors
E   ModuleNotFoundError: No module named 'refitt.core.web'             (13 files)
E   ModuleNotFoundError: No module named 'refitt.data.broker'          (2 broker files)
E   ImportError: cannot import name 'ObservationPublishApp' from 'refitt.admin'
!!!!!!!!!!!!!!!!!!! Interrupted: 16 errors during collection !!!!!!!!!!!!!!!!!!!
```

Every symbol still exists at a new home, so the repair is a pure rename:

| legacy import | new home |
|---|---|
| `refitt.core.web.{token,request,response}` | `refitt.api.{token,request,response}` |
| `refitt.web.api` (`INFO`) | `refitt.server` (re-exported, `refitt/server/__init__.py:24`) |
| `refitt.web.api.recommendation` | `refitt.server.route.recommendation` |
| `refitt.data.broker.{alert,antares,client}` | `refitt.broker.{alert,antares,client}` |
| `from refitt.admin import ObservationPublishApp` | `refitt.admin.observation.publish` |
| `tests.test_data.test_broker.test_alert.MockAlert` | `py/apps/refitt-broker/tests/test_alert.py:111`. Move it into a conftest/helper when re-homing. |

**The suite is recoverable.** On a codemodded copy:

| scenario | result |
|---|---|
| collect only | 1218 root+broker tests collected; **909 were hidden behind the 16 errors** |
| ephemeral postgres:16 + live server, real `HOME` | 740 failed, 476 passed; 633× `Missing 'api.rootkey'` (developer config leak, below) |
| isolated `HOME` | 16 failed, 1200 passed (all timezone) |
| isolated `HOME` + `PGTZ`/`TZ` = `America/Indiana/Indianapolis` | **1216 passed, 2 skipped, 0 failed** |

The whole suite is about 1,278 tests: 1218 root and broker, 25 tns, 20 factory, 15 host.

**Environment defects the run exposed:**
- **Session timezone.** Seed data and expected values are literal `-04:00` strings (e.g. `epoch.json`
  `'2020-10-24 20:01:00-04:00'`). The Postgres service runs in UTC.
  - `tests.yml:48` sets `TZ` for the runner only; libpq ignores it, and the service has no `PGTZ`.
  - The legacy zone name `America/Indianapolis` is rejected by the postgres image (`FATAL: invalid
    value for parameter "TimeZone"`); use the canonical IANA name everywhere.
  - SQLite stores strings verbatim, which hides all of this.
  - (`86e0890`, 2022, "fixed" it with `szenius/set-timezone`, which only touched the runner.)
- **Developer config leaks into tests.**
  - A `rootkey_eval` key in `~/.refitt/config.toml` makes cmdkit raise "'rootkey' has more than one
    variant" when an env `rootkey` coexists (`namespace.py:79-94`). `token.py:85-88` then reports it
    as "Missing".
  - An env layer cannot override `*_eval`/`*_env` keys, so tests need an isolated `HOME`.
  - `refitt.core.platform` creates `~/.refitt/{lib,run,log}` at import (`platform.py:42-46`).
- **Read and write sessions are the same object under test config.** CI, `temp_db.sh` and
  `temp_pg.sh` all set read=write=`default`, so `db.read is db.write` and session-scoping bugs are
  never exercised.

**Structure defects:**
- **Markers.** 53% of tests are untagged: 224 of 255 model tests, 439 of 813 endpoint tests, all 15
  refitt-host tests. The factory's canonical fast-tier command
  (`temp_db.sh sh -c "uv run pytest -m unit tests/test_database"`) therefore selects only 21 config
  tests, so **fast-tier verification of model changes is vacuous**. `--strict-markers` rejects
  unknown markers but not missing ones.
- **Config.** The root `pyproject.toml:103-109` is the effective pytest config. It has no
  `testpaths` and carries a decoy `parameterize` marker. Eight member pyprojects carry identical dead
  copies of that block.
- **Location.** Tests live away from the distributions they exercise, and helpers are shared across
  directories. `json_roundtrip` is used 20 times, `TestData` 19, `Endpoint`/`LoginEndpoint` 11, and
  the DB-mutating context managers 3. `tests/test_database/conftest.py:15-21` shadows the built-in
  `tmpdir` with a fixed `/tmp/refitt/tests/<date>` and never cleans up.
- **Endpoint tests are end-to-end over HTTP** against a live `refitt-server` sharing the seeded
  database (813 tests). They have no per-test isolation, and they assert 215 exact message strings.
- Two refitt-host tests depend on the working directory; see
  [`refitt-host-conform.md`](refitt-host-conform.md).

## Why it was deferred

These defects predate the factory. CI was modernized first (`8422947`) and runs honestly red, with
no `continue-on-error`. The repair was planned as the factory's first dogfood cycle. Every item is
**pre-existing**.

## Outcome / vision

`uv run pytest` collects everything and passes against both verify tiers. Each test lives with the
distribution it exercises, under one pytest config. Every test is tagged, so `-m unit` and
`-m integration` select real, meaningful subsets. The test environment is isolated from the
developer's `HOME` and config, and timezone handling is explicit.

## Sketch of the acceptance criteria

- **R1** — WHEN `uv run pytest --collect-only` runs from the repo root, collection SHALL report zero
  errors.
- **R2** — WHEN the full suite runs under `temp_pg.sh` with the server, it SHALL pass with zero
  failures.
- **R3** — Every collected test SHALL carry exactly one of `unit` / `integration`.
- **R4** — WHEN the suite runs with a developer `~/.refitt/config.toml` present, results SHALL be
  identical to a run without one.
- **R5** — WHEN CI runs on `develop`, the tests job SHALL pass on Python 3.12 and 3.13.
- **R6** — Each test file SHALL live under the distribution whose code it exercises, except the
  factory tests, which stay at the root.

## Notes

- The verify scripts are under `.agents/` and can only change through `/rf-harness`.
  - `temp_db.sh` cannot run unattended today. `init` always prompts on SQLite (`init.py:75-78`:
    `host` is always `None`), a user config conflicts with the forced settings
    (`core.py:100-101`), and the `cd "$site"` at line 38 breaks the documented relative paths.
  - `temp_pg.sh` needs `HOME` isolation, an always-exported ephemeral rootkey, `PGTZ`, free ports
    bound to `127.0.0.1`, host-side readiness probes, a `docker info` check, and `UV_NO_SYNC`/frozen.
  - Run that harness pass first, or this cycle has no working verify substrate. The deferred
    item is in `.agents/factory/harness-log.md`.
- Codemod and re-home map from the sweep:
  - `test_core/test_schema.py` → core
  - `test_core/test_web.py` → api
  - `test_database/**` → data
  - `test_web/**` → server (an empty `py/apps/refitt-server/tests/` exists untracked)
  - `test_app/**` and `test_forecast.py` → admin
  - `test_factory_fsm.py` stays at the root
- Related: [`workspace-install-hygiene.md`](workspace-install-hygiene.md) (CI dies before pytest
  until it lands), [`api-app-factory.md`](api-app-factory.md) (hermetic endpoint tests),
  [`seed-dataset-v2.md`](seed-dataset-v2.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
