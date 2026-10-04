---
status: unshaped
kind: fix
appetite: small
lane: public
---

# `refitt database init --core` leaves a database unable to ingest

## Problem

The core seed role ships nine files under `py/libs/refitt-assets/src/refitt/assets/database/core/`:
`file_type`, `level`, `model_type`, `object_type`, `observation_type`, `source_type`, `source`,
`topic`, `user`. But `ENTITIES['core']` (`py/libs/refitt-data/src/refitt/database/__init__.py:59`)
loads only five: `['user', 'object_type', 'model_type', 'level', 'topic']`. A database initialized
with `refitt database init --core` therefore has no `file_type`, `observation_type`, `source_type`
or `source` rows.

Code that looks those rows up by name then fails with NotFound on such a database:
- **Broker ingest:** `Source.from_name(source_name)` and `ObservationType.from_name`
  (`py/apps/refitt-broker/src/refitt/broker/alert.py:181,189`).
- **`POST /recommendation/<id>/observed`:** `Source.get_or_create` →
  `SourceType.from_name('observer')` (`model.py:882`).
- **Forecast publishing:** needs `ModelType`, `Source` and `ObservationType` by name
  (`refitt/forecast/model.py:38-50`).

Related rough edges on the same path:
- `--core` and `--test` are a mutually exclusive group (`admin/database/init.py:58-60`), and `--test`
  loads only the test role. The factory's `ears.md` example says `--test` "additionally" loads the
  test seed, which is wrong.
- `core/source.json` stores `"data": "{}"`, a string rather than a JSON object.
- The remote-database prompt shows `[Y]/n`, but an empty answer raises `RuntimeError('Missing
  confirmation')` (`init.py:75-78`). The capital Y promises a default it does not honor.
- Two broker tests read `core/observation_type.json` and `core/object_type.json` directly
  (`py/apps/refitt-broker/tests/test_alert.py:64,71`). They are the only consumers of the orphaned
  files today.

Whether production was ever initialized with `--core` alone is not recorded in this repository; it
may have been seeded some other way. The defect is in what `--core` does, whatever production did.

## Why it was deferred

Found during the roadmap evidence sweep, outside any cycle. **Pre-existing** on `develop`.

## Outcome / vision

`--core` produces a database every REFITT service can run against. The test role is a superset
built on the same core reference data, not a parallel copy. The flags' help text says what they do.

## Sketch of the acceptance criteria

- **R1** — WHEN `refitt database init --core` runs against an empty database, the database SHALL
  contain every row the core seed files define.
- **R2** — WHEN broker ingest processes an alert against a database initialized with `--core`, it
  SHALL NOT fail for a missing source or observation type.
- **R3** — Every file under `database/core/` SHALL either be loaded by `--core` or be removed.
- **R4** — `refitt database init --help` SHALL describe exactly which roles each flag loads.

## Notes

- Keep it small. The seed-dataset v2 cycle reworks the loader, keys and roles wholesale; this fix
  only makes today's `--core` complete. Load order must respect FKs (`source` → `source_type`,
  `user`); `Entity.metadata.sorted_tables` already gives a topological order (used at
  `admin/database/check.py:57`).
- The `ears.md` correction is a `/rf-harness` edit.
- Related: [`seed-dataset-v2.md`](seed-dataset-v2.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
