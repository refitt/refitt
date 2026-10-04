---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Move authorization out of individual routes into one policy layer

## Problem

Authorization has two halves today:
- **The coarse gate:** one integer threshold, `client.level > level` → `PermissionDenied`
  (`server/auth.py:78-92`). Lower is more privileged. 46 routes require no level, 19 require ≤ 1, and
  3 require 0.
- **Everything finer is written inline in the route:**
  - `is_owner` (`route/recommendation.py:67-70`, with a "TODO: is this right?")
  - `is_viewable` (`route/observation.py:61-63`)
  - `is_associated` (`route/model.py:43-54`)
  - `_get_source` (`route/source.py:34-40`)
  - assorted inline checks

**Consequences:**
- **No single place says who may see or change what.** A reviewer has to read every route to answer
  it, and the portal will multiply the routes.
- **The admin bypass is applied inconsistently.** For example, `GET
  /recommendation/<id>/observed/file/type` has none (`route/recommendation.py:485-487`), while its
  siblings do.
- **One visibility rule depends on seed load order** (`obs.source.type_id != 4`); see
  [`seed-dataset-v2.md`](seed-dataset-v2.md).
- **Rules are tested only as far as the tests happen to exercise each route.** Several routes are
  tested only as admin.

## Why it was deferred

It depends on the app factory (a natural place to install a policy layer) and on seed-v2 personas
(to test it as a matrix). **Pre-existing.**

## Outcome / vision

A policy module states every resource-level rule once, including ownership, visibility, admin
bypass, and any constraint between privilege levels. Routes call it rather than embedding checks. A
generated test matrix covers every route × persona from the seed, so any change to a rule shows up
as a test diff.

## Sketch of the acceptance criteria

- **R1** — Every route SHALL obtain its authorization decision from the policy layer.
- **R2** — WHEN the persona matrix test runs, every route × persona combination SHALL produce the
  decision the policy specifies.
- **R3** — No authorization decision SHALL depend on a database row's position or a literal ID.
- **R4** — WHEN an admin persona requests any resource a non-admin owner can read, the admin SHALL be
  allowed, unless the policy explicitly records an exception.

## Notes

- Specific weaknesses found during the sweep are tracked in the private security lane, not here. Read
  `.security/` (maintainer-local) before shaping, and fold the remediations in or sequence them
  first.
- Related: [`api-app-factory.md`](api-app-factory.md),
  [`portal-auth-sessions.md`](portal-auth-sessions.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
