---
status: unshaped
kind: feature
appetite: big
lane: public
---

# Give the schema a migration path (§C2)

## Problem

The schema lifecycle is `Entity.metadata.create_all()` / `drop_all()` and nothing else
(`database/__init__.py:40-49`). Its only caller is `refitt database init` with optional `--drop`
(`admin/database/init.py:79-85`). `alembic` is not in `uv.lock`. Backfills are hand-written ORM
scripts (`py/scripts/update_pred_type.py:59-81`).

Every structural change the portal needs requires a migration:
- **More than one session per client, and more than one credential per user.** This means dropping
  the unique constraints on `Session.client_id` (`model.py:559-560`) and `Client.user_id`
  (`model.py:454`).
- **Tables for human login**, and the JSON → JSONB conversion
  ([`db-dialect-parity.md`](db-dialect-parity.md)).
- **Removing the six vestigial StreamKit tables** (`model.py:1521-1690`). The StreamKit integration
  is commented out (`core/config.py:23,269-278`); `level` and `topic` are still seeded.
- **Any rename the data-model redesign makes.**

**Design constraints:**
- **Production's live schema is unknown from this repository.** There are hints of drift: a
  commented-out TimescaleDB variant of `Message` with a different primary key
  (`model.py:1608-1617,1637-1643,1736-1739`), and provider aliases `timescale`/`timescaledb`
  (`connection.py:43-44`). Baselining (`alembic stamp`) requires diffing the live schema against the
  ORM first.
- **Schema names come from config at class-definition time** (`model.py:64-67`, invariant §4).
  Migrations need `include_schemas` and a `version_table_schema` that follow config.
  - Per-scope schemas (`database.read.schema` / `database.write.schema`) are ignored for table
    binding.
  - `refitt database check` resolves the schema differently (`admin/database/check.py:84`).
- **SQLite needs Alembic batch mode** for ALTERs.
- **Tests build the schema with `create_all`.** That is a different DDL path from the one a
  migration-driven production takes, unless test databases are built with `upgrade head`.
- `DatabaseConfiguration.encode()` builds URLs without percent-encoding (`core.py:113-147`), so a
  password containing `@` or `/` breaks the URL a migration environment would reuse.

## Why it was deferred

Invariant §C2 ("no migration system") is a Tier 2 current constraint, and this is the redesign. It
needs the test suite working first, and a look at production. **Pre-existing.**

## Outcome / vision

Schema changes ship as reviewed, reversible migrations. Production is baselined against the ORM. Test
databases are built through the same migration path production uses. `refitt database` gains
upgrade, downgrade and status commands with documented behavior. §C2 is retired from
`invariants.md` through `/rf-harness`.

## Sketch of the acceptance criteria

- **R1** — WHEN `refitt database init` creates a new database, the resulting schema SHALL equal the
  schema produced by applying every migration from empty.
- **R2** — WHEN a migration is applied and then reverted on a seeded test database, the schema and
  rows SHALL return to their prior state.
- **R3** — WHEN the migration tooling runs with a configured schema name, the version table and all
  tables SHALL live in that schema.
- **R4** — WHEN the ORM and the migration head diverge, a check in CI SHALL fail.
- **R5** — A documented procedure SHALL baseline an existing production database without altering its
  data.

## Notes

- Shaping decisions:
  - Alembic (the default for SQLAlchemy) or something else.
  - Whether SQLite stays a supported migration target or becomes a fast-test-only `create_all`
    target.
  - Whether the StreamKit tables are dropped in the first revision.
  - How production is inspected, and who does it.
- Touches `database/{model,connection,core}.py` and `core/config.py`, all high-blast-radius. A
  change to *when* schema and connection bind is a §4 amendment, not a deviation.
- Related: [`model-derive-columns.md`](model-derive-columns.md),
  [`db-dialect-parity.md`](db-dialect-parity.md), [`seed-dataset-v2.md`](seed-dataset-v2.md),
  [`portal-auth-sessions.md`](portal-auth-sessions.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
