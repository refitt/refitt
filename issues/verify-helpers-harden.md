---
status: unshaped
kind: test
appetite: small
lane: public
---

# Harden the throwaway-environment helpers

## Problem

`tools/temp_db.sh` (the fast SQLite tier) and `tools/temp_pg.sh` (the faithful Postgres tier) are
the verify substrate every cycle runs on (`AGENTS.md` § Factory → Throwaway environment). Neither
meets that contract today. The 2026-10-04 evidence sweep of `develop` at `8e85fc8` found:

- **`temp_db.sh` cannot run unattended.** `refitt database init` always prompts on SQLite
  (`init.py:75-78`: `host` is always `None`). A user config that adds `host`/`user` to
  `database.default` conflicts with the forced settings (`database/core.py:100-101`), so the
  developer's real config leaks in (contract item 3). The `cd "$site"` breaks the documented
  relative test paths (`tests/…`).
- **`temp_pg.sh` leaks the developer's config.** It needs:
  - `HOME` and config isolation (a developer `rootkey_eval` leaks in);
  - an always-exported ephemeral rootkey;
  - `PGTZ`;
  - free ports bound to `127.0.0.1` rather than a fixed `5544` on `0.0.0.0`;
  - host-side readiness probes rather than only `pg_isready` inside the container;
  - a `docker info` daemon check;
  - `UV_NO_SYNC` or `--frozen`, so a verify never re-locks `uv.lock`.

Both helpers moved from `.agents/factory/bin/` to `tools/` when the repo adopted the KB harness
(2026-11-09); their contents did not change. **Pre-existing.**

## Why it was deferred

It was found by an out-of-cycle evidence sweep, recorded then as a deferred harness item. At
adoption it became an ordinary seed, because the helpers are now repository code.

## Outcome / vision

Either helper runs any command hermetically and unattended, on a developer machine with a populated
`~/.refitt`, and leaves nothing behind. The test-suite cycle can then use it as its verify.

## Sketch of the acceptance criteria

- **R1** — WHEN `tools/temp_db.sh <cmd>` runs with no TTY, it SHALL complete without prompting.
- **R2** — WHEN either helper runs with a developer `~/.refitt/config.toml` present, the command
  SHALL see only the throwaway configuration.
- **R3** — WHEN `tools/temp_pg.sh` starts Postgres, it SHALL bind a free port on `127.0.0.1` and
  wait for a host-side connection to succeed before running the command.
- **R4** — WHEN either helper exits by any path, its state directory and container SHALL be gone,
  and the command's exit status SHALL pass through.

## Notes

- Related: [`test-suite-repair.md`](test-suite-repair.md) (depends on this),
  [`db-dialect-parity.md`](db-dialect-parity.md) (revisits the tier split).
- Found by: the out-of-cycle evidence sweep, 2026-10-04.
