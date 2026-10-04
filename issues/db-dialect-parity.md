---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Make SQLite and Postgres agree, or say exactly where they don't (§C4)

## Problem

REFITT verifies on two tiers: `temp_db.sh` (SQLite) and `temp_pg.sh` (Postgres). Production is
Postgres. The dialects diverge in ways the fast tier silently hides:

- **`JSON` is not `JSONB`.** `from sqlalchemy.dialects.postgresql import JSON as SQLJSONB`
  (`model.py:26`) imports Postgres **`json`**, then `JSON = SQLJSON().with_variant(SQLJSONB(),
  'postgresql')` (`model.py:211`) applies it to ten columns across seven models.
  - Postgres `json` has no GIN indexing, no `@>`, and **no equality operator**.
  - `refitt database query 'object.aliases -> tag == x'` compiles to
    `col[...] == type_coerce(v, JSON)` (`admin/database/query.py:527-533`), which should fail on
    Postgres with "operator does not exist: json = json" [static: not executed in the sweep].
- **The raw `->>` operator appears once:** `Object.from_alias` →
  `Object.aliases.op('->>')(provider) == name` (`model.py:711`), behind `Object.from_name` and
  `add_alias`. In-memory SQLite 3.53 accepts `->>` with both `'ztf'` and `'$.ztf'`.
  - So the "Postgres-only `->>`" premise behind the two-tier verify guidance (`temp_db.sh:11-13`,
    `methodology.md`, `ears.md`) is stale for SQLite ≥ 3.38.
  - SQLAlchemy's portable `aliases[provider].as_string()` would remove the `.op()` call entirely.
- **SQLite runs without foreign keys.** There is no `PRAGMA foreign_keys=ON` and no
  `event.listens_for` anywhere in the workspace. An FK-violating insert is accepted. As a result,
  `ondelete='cascade'` (FacilityMap, Session), FK `IntegrityError` paths, and the
  `ConstraintViolation → 400` mapping all behave differently across the two tiers.
- **Timestamps differ.**
  - `DateTime(timezone=True)` (`model.py:215`) is aware on Postgres and naive on SQLite.
  - `server_default=func.now()` is aware `now()` on Postgres but naive UTC `CURRENT_TIMESTAMP` on
    SQLite.
  - `to_json` emits `str(datetime)` (`core.py:194-199`), so **API timestamp strings depend on the
    backend**.
  - The seed loader only re-parses `'%Y-%m-%d %H:%M:%S%z'` (`core.py:184-191`), so values with
    microseconds or without a timezone don't round-trip.
- `BIG_INTEGER = Integer().with_variant(BigInteger(), 'postgresql')` (`model.py:208`) is a
  deliberate divergence so SQLite gets rowid autoincrement. Keep it documented.

## Why it was deferred

Invariant §C4 is a Tier 2 current constraint. The JSONB conversion is a schema change and needs
[`db-migrations.md`](db-migrations.md). **Pre-existing.**

## Outcome / vision

Postgres uses `jsonb`, and JSON access is portable. SQLite enforces foreign keys. Timestamps are
timezone-aware end to end and serialize identically on both dialects. The factory's verify guidance
states the *real* remaining dialect gaps, so a phase picks its tier on facts. §C4 is retired or
rewritten through `/rf-harness`.

## Sketch of the acceptance criteria

- **R1** — WHEN the schema is created on Postgres, every JSON column SHALL be `jsonb`.
- **R2** — WHEN `refitt database query` filters on a JSON field by equality, it SHALL return the
  matching rows on both dialects.
- **R3** — WHEN a row violating a foreign key is inserted on the SQLite tier, the insert SHALL fail
  as it does on Postgres.
- **R4** — WHEN the same seeded row is serialized on either dialect, its timestamp strings SHALL be
  identical.
- **R5** — No model method SHALL use a raw dialect operator where a portable SQLAlchemy construct
  exists.

## Notes

- The verify-substrate prose (`temp_db.sh` header, `methodology.md`, `ears.md`) is a `/rf-harness`
  edit; land it with this cycle.
- The timestamp serialization format is also an API contract change. Coordinate with
  [`api-serialization-layer.md`](api-serialization-layer.md) so clients see one change, not two.
- Related: [`seed-dataset-v2.md`](seed-dataset-v2.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
