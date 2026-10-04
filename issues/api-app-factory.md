---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Build the server per app instance, with request-scoped sessions

## Problem

- **One global app, routes by side effect.** `refitt-server` has a single global Flask `application`
  (`server/app.py:29`). Its 69 routes register through import side effects (`route/__init__.py:13-16`,
  `server/__init__.py:23-24`), so importing `refitt.server.app` alone yields an app with *no*
  routes.
- **Database bound at import (§4).** Config loads at import (`core/config.py:220-224`, with
  `sys.exit(bad_config)`). `database.connection.default_connection` is constructed at import
  (`connection.py:157-161`), and table schemas bind at class definition (`model.py:64-67`).
- **No hermetic endpoint tests.** Together, these make per-test apps or per-test databases
  impossible. The 813 endpoint tests run end-to-end over HTTP against a live server sharing one
  seeded database, mutating shared rows through context managers. They have no transaction
  isolation and no Flask `test_client`.
- **Sessions are not request-scoped.**
  - `model.py` has 65 implicit global-session fallbacks (`session or db.read` ×46,
    `session or db.write` ×19) and 20 `session.commit()` calls inside model methods. A route cannot
    compose writes atomically: `POST /recommendation/<id>/observed` commits `Observation.add` and
    then, separately, `Recommendation.update` (`route/recommendation.py:542-545`).
  - `User.delete` and `Facility.delete` cascade by hand, committing row by row
    (`model.py:298-322,398-413`).
- **§7 is already broken.** `after_request` closes `db.read` for GET and `db.write` otherwise
  (`server/app.py:56-65`). But four GET routes write (`route/token.py:29-30,56-61`;
  `route/client.py:30-35,69-74`), and their write session is never closed. Several mutating routes
  read through `db.read` defaults (e.g. `route/user.py:400`, `route/recommendation.py:429,529`).
  Tests cannot see any of this, because test config makes `db.read is db.write`.
- **The dev server is what tests and verify run.** Production runs gunicorn (`server/__init__.py:114-118`),
  while `--dev` runs the Flask debug server, which CI and `temp_pg.sh` use. There is no proxy
  handling, request IDs, or structured access log.

## Why it was deferred

Every part of this amends a Tier 1 invariant: §6 names the single global app with no Blueprints and
the `refitt.server:app` WSGI target; §4 names import-time binding and fail-fast; §7 names the
session scoping. It needs a constitution change through `/rf-harness` alongside the code, under a
human gate. **Pre-existing.**

## Outcome / vision

`create_app(config)` builds an app with Blueprints, owns its own engine and sessions, and keeps the
fail-fast guarantees at app-build time rather than import time. Each request gets one session (unit of
work) that commits or rolls back at the end, so model methods stop committing. Endpoint tests use the
Flask test client against a per-test transaction or database. The production WSGI target still
exists.

## Sketch of the acceptance criteria

- **R1** — WHEN `create_app` is called twice with different database configs, the two apps SHALL
  serve requests against their own databases without interfering.
- **R2** — WHEN a route performs several writes and one fails, none of the writes SHALL be
  committed.
- **R3** — The endpoint test suite SHALL run without a separately started server.
- **R4** — WHEN the server is started with a bad configuration, it SHALL still exit with
  `exit_status.bad_config` before serving.
- **R5** — The production WSGI entry point SHALL continue to work unchanged for deployment.

## Notes

- Moving the GET routes that mint or rotate credentials to POST is a protocol change; it lives in
  [`portal-auth-sessions.md`](portal-auth-sessions.md).
- Touches `server/{app,endpoint,tools}.py`, `route/*.py`, `database/{model,connection}.py` and
  `core/config.py`, all high-blast-radius. Expect a long human-gated review.
- Related: [`test-suite-repair.md`](test-suite-repair.md),
  [`api-serialization-layer.md`](api-serialization-layer.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
