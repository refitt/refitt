---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Derive model column and relationship metadata from the mapper (§C1)

## Problem

`py/libs/refitt-data/src/refitt/database/model.py` (1739 lines, 25 models, 118 mapped columns, 33
FKs) keeps a hand-written `columns` dict on every model, and a `relationships` dict on 12 of them,
duplicating the SQLAlchemy mapping. That is invariant §C1's dual source of truth.

**Parity is clean today.** An AST check found the `columns` keys equal to the mapped attributes, in
declaration order, for all 25 models. The `relationships` keys equal the `relationship()` attributes
for all 12. The dict *values* (Python types) are never read; only the keys and their order matter.

**Consumers, i.e. what breaks if the dicts change:**
- **Model layer.** `__repr__`, `to_tuple` and `to_dict` iterate `columns` (`model.py:72-83`).
  `to_json(join=True)` iterates `relationships` (`model.py:100-118`).
- **`EntityMixin.update`** routes any field not in `columns` into the `data` JSON column
  (`model.py:152-168`).
  - The API depends on this. `PUT /user/<id>` and `PUT /facility/<id>` accept arbitrary fields
    (`route/user.py:214`, `route/facility.py:130`, documented as `'*': Arbitrary field added to JSON
    data`).
  - Models without a `data` column would raise there.
- **`refitt database query` CLI** (`admin/database/query.py:224-487`) uses both dicts.
  - It inverts `relationships` (`:289`), which collapses Recommendation's two Observation links.
  - It assumes the first column is `id` (`:249,373`), which is false for the composite-key
    FacilityMap and Access.
- **Tests.** `test_tuple` asserts `tuple(seed_json.values()) == record.to_tuple()`. That hides a
  three-way lockstep between seed JSON key order, `columns` order, and mapped-column order (§C3).

**The derivation hazard.** `inspect(Model).relationships` also returns the **28 backrefs** (e.g.
`backref='client'` at `model.py:461`). The 31 hand-listed relationships are exactly the
**MANYTOONE** ones. Filtering on direction reproduces today's dicts; any other choice changes every
`to_json(join=True)` payload, and the join can recurse (User → client → user → …).

**Adjacent debt in the same file:**
- The legacy `sqlalchemy.ext.declarative.declarative_base` (`model.py:23,204`), deprecated since
  SQLAlchemy 2.0.
- `pandas` imported at module top just for `_query_realtime` (`model.py:20,1420-1463`).
- `Alert.data` annotated `Mapped[int]` but actually JSON (`model.py:1007`).
- Recommendation state stored as two unconstrained booleans, `accepted` and `rejected`
  (`model.py:1287-1288`).

## Why it was deferred

Invariant §C1 is a Tier 2 "honor until redesigned" constraint, and this is the redesign. Model
tests cannot verify it today (224 of 255 model tests are untagged; see
[`test-suite-repair.md`](test-suite-repair.md)). **Pre-existing.**

## Outcome / vision

The mapper is the only source of column and relationship metadata. Serialization, `update()`, and
the query CLI keep their observable behavior. §C1 is retired from `invariants.md` through
`/rf-harness`.

## Sketch of the acceptance criteria

- **R1** — No model SHALL declare a hand-written `columns` or `relationships` dict.
- **R2** — WHEN any model is serialized with `to_json()` or `to_json(join=True)`, the payload SHALL
  be identical, keys and order included, to the pre-change payload for the same seeded row.
- **R3** — WHEN `PUT /user/<id>` or `PUT /facility/<id>` receives a field that is not a column, it
  SHALL be stored in `data` as before.
- **R4** — WHEN `refitt database query` targets a model with two relationships to the same table, or
  a composite primary key, it SHALL return correct results.
- **R5** — The model module SHALL import without pandas installed. *(Shaping decision: whether this
  is in scope.)*

## Notes

- `model.py` is on the high-blast-radius list (AGENTS.md §6), so `/rf-plan` runs the full research
  fan-out regardless of appetite. Every CONFIRMED review finding needs human sign-off.
- Drop the six vestigial StreamKit tables (Level, Topic, Host, Message, Subscriber, Access;
  `model.py:1521-1690`, unused outside `model.py`) in the migrations cycle, not here: removing
  tables is a schema change.
- Related: [`db-migrations.md`](db-migrations.md),
  [`api-serialization-layer.md`](api-serialization-layer.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
