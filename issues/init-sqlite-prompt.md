---
status: unshaped
kind: fix
appetite: small
lane: public
---

# `refitt database init` asks for confirmation on every SQLite database

## Problem

`refitt database init` guards a remote database with a confirmation prompt
(`py/apps/refitt-admin/src/refitt/admin/database/init.py:75-78`):

```python
if 'host' in db_cfg and db_cfg.host not in ('localhost', '127.0.0.1'):
    response = input(f'Connected to remote database ({db_cfg}), proceed ([Y]/n): ')
```

`db_cfg` is a `DatabaseConfiguration`, which always carries a `host` key: `None` when unset
(`py/libs/refitt-data/src/refitt/database/core.py:63`). SQLite validation forbids a host
(`core.py:100-104`), so on SQLite `host` is always `None`, `None` is never in the local tuple, and
the prompt fires on every SQLite database. A local Postgres reached through a Unix socket (no
`host`) gets the same prompt. The prompt goes to stdout, and with no terminal `input()` either
blocks on a pipe or raises `EOFError` on `/dev/null`, so `init` cannot run unattended against a
file database.

Observed on `develop` at `aa7623d`: with a forced SQLite config and stdin from `/dev/null`, `init`
prints `Connected to remote database (sqlite:////…/refitt.db), proceed ([Y]/n): ` on stdout, then
logs `EOFError: EOF when reading a line` and exits 6. With `y` piped in, it proceeds.

## Why it was deferred

The verify-helpers-harden cycle met its unattended-SQLite requirement on the helper side:
`tools/temp_db.sh` answers the prompt itself and sends `init`'s stdout to stderr. That GOAL put any
change under `py/` out of scope, so the product fix waits for a cycle of its own. **Pre-existing**
on `develop`.

## Outcome / vision

`init` asks only when it is about to touch a database on another host. SQLite files and local
Postgres, by TCP or socket, initialize without a prompt, and an unattended run against a remote
database fails with a clear message instead of hanging.

## Sketch of the acceptance criteria

- **R1** — WHEN `refitt database init` runs against a SQLite database, it SHALL NOT prompt.
- **R2** — WHEN it runs against Postgres on `localhost`, `127.0.0.1` or a Unix socket, it SHALL NOT
  prompt.
- **R3** — WHEN it runs against a remote host with no terminal on stdin, it SHALL exit non-zero with
  a stderr message naming the host, without waiting for input.
- **R4** — WHEN this lands, `tools/temp_db.sh` SHALL stop answering the prompt, and its header and
  `AGENTS.md` § Factory → Throwaway environment SHALL drop the mention of it.

## Notes

- The same prompt shows `[Y]/n` but treats an empty answer as a refusal; that half is recorded in
  [`core-seed-incomplete.md`](core-seed-incomplete.md). Shape the two together or say which owns it.
- A §K6 change: `init`'s `--help` and the docs change with it.
- Related: `spec/verify-helpers-harden/` (the helper-side workaround).
- Found by: `verify-helpers-harden` shaping and plan, 2026-11-09.
