---
status: unshaped
kind: test
appetite: big
lane: public
---

# A seed dataset that can exercise the portal (§C3)

## Problem

The seeds live in `py/libs/refitt-assets/src/refitt/assets/database/{core,test}/*.json`. The test
role holds 323 records across all 21 `ENTITIES['test']` tables; 94 of them are reference/type rows.

**Positional keys.**
- Every record has `"id": null`, so IDs are assigned by load order and every foreign key in the
  seeds is a hard-coded position.
- Changing array order, adding a row early, or reordering `ENTITIES` silently re-points FKs.
- **One authorization rule depends on that order:** `is_viewable` hard-codes
  `obs.source.type_id != 4`, i.e. 'observer' being the 4th `source_type` row
  (`route/observation.py:59-63`). The comment above it wrongly says "user_id == 1".
- Implicit lockstep set (§C3): `ENTITIES` names = `tables` keys = asset basenames; array order fixes
  IDs; JSON key order = `columns` order (because of `test_tuple`).

**Duplicated reference data.**
- The seven reference tables (file_type, level, model_type, object_type, observation_type,
  source_type, topic) are byte-identical copies in `core/` and `test/`.
- The test role is a parallel dataset, not core plus fixtures. Test user 1 is 'superman' (a level-0
  client), while core user 1 is the 'refitt' system user.

**Too thin for the portal:**

| Need | Present | Gap |
|---|---|---|
| Pending recommendations | 24, **all `accepted=True`**, none rejected | `Recommendation.next` filters to unaccepted and unrejected (`model.py:1486-1487`), so **`GET /recommendation` returns `[]` for every seeded user**. `data` is `{}` everywhere, so realtime mode (`model.py:1434`, airmass) always returns `[]`. |
| Forecasts | 24 models, all type 1, **`data: {}`** | No light-curve payloads; model type 2 unused. Forecast views cannot be tested. |
| Objects | 10 ZTF-2020 objects, all type 'Unknown' | No classified objects, no redshifts, empty history. |
| Observations | 78 over 4 days in Oct 2020 | No provisional (`value=null`) rows; nothing recent, so time-relative features are untestable. |
| Alerts / files | 30 alerts with empty properties; 24 tiny base64 stubs | Not representative of real payload shapes. |
| Identity / privilege | 4 users: 1 at level 0, 3 at level 10 | **No level-1 admin**, though 19 routes gate on level ≤ 1. No revoked client, no user without credentials. |
| Hygiene | Fictional users on real domains (dailyplanet.com, cia.gov, croft.net, cam.ac.uk) | Should be RFC 2606 domains. |

**Loader quirks** (`core.py:184-239`):
- Strings matching `%Y-%m-%d %H:%M:%S%z` become datetimes.
- **Any top-level list of strings becomes base64-decoded bytes**, including the empty list
  (`all([])` is True) (`core.py:202-207`).
- `load_defaults` commits once per entity with one session (`database/__init__.py:67-75`).

## Why it was deferred

Invariant §C3 is a Tier 2 current constraint. A real dataset should be co-designed with the migrated
schema and dialect decisions ([`db-migrations.md`](db-migrations.md),
[`db-dialect-parity.md`](db-dialect-parity.md)), not built twice. **Pre-existing.**

## Outcome / vision

The seed is built on core reference data and loaded through the same path production uses. It uses
explicit or natural keys and has no positional FKs. It includes a persona matrix (levels 0, 1, 10, a
revoked client, a user without credentials), recommendations in every state, forecast models with
real payloads, provisional and recent observations with dates relative to now, and RFC 2606
identities. It is large enough to drive portal tests and small enough to load in seconds.

## Sketch of the acceptance criteria

- **R1** — No seed record SHALL depend on load order for its primary key or for any foreign key.
- **R2** — No authorization rule SHALL depend on a seed row's position.
- **R3** — WHEN the test seed is loaded, `GET /recommendation` SHALL return a non-empty list for at
  least one non-admin persona.
- **R4** — The test seed SHALL include at least one persona at each privilege level any route gates
  on, and at least one revoked client.
- **R5** — Reference data SHALL be defined once and shared by the core and test roles.
- **R6** — WHEN the test seed is loaded into a database whose name or config does not mark it as a
  test database, the loader SHALL refuse.

## Notes

- The test suite asserts 44 seed counts, references seed aliases by literal
  (`tomb_raider` 114×, `superman` 67×), and uses 91 literal `/resource/<int>` routes. Plan the test
  migration with the dataset, not after it.
- Related: [`core-seed-incomplete.md`](core-seed-incomplete.md) (the small fix that lands first),
  [`authz-policy-layer.md`](authz-policy-layer.md) (personas drive its test matrix),
  [`test-suite-repair.md`](test-suite-repair.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
