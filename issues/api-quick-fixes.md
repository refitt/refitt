---
status: unshaped
kind: fix
appetite: small
lane: public
---

# Small API defects that do not need the redesign

## Problem

Three independent defects in `refitt-server` / `refitt-api`. Each is observable by a client and
fixable without the Part IV redesign:

1. **A malformed bearer token returns 500 instead of 403.**
   - `JWT.decrypt`'s error path builds `Token(_token.decode())`, which raises `ValueError` when the
     value does not match the token pattern (e.g. contains `.`, `+`, `/`, or is empty)
     (`py/libs/refitt-api/src/refitt/api/token.py:331-332`, pattern at `:110`).
   - `ValueError` is not in `RESPONSE_MAP` (`api/response.py:116-133`), so `@endpoint`
     (`server/endpoint.py:41-50`) answers `{"Status": "Critical"}` with 500.
   - Invariant §5 says a missing, malformed or expired token is a 403.
2. **`PayloadTooLarge` (413) is raised for invalid query parameters** on GET routes at five sites
   (`route/observation.py:76,82`, `route/model.py:72,74`, `route/epoch.py:42`). A bad `limit` on a
   GET has no payload; it is a 400.
3. **Errors raised outside `@endpoint` are not enveloped.** Only 404 and 405 have enveloped handlers
   (`server/app.py:32-47`). Other Werkzeug errors, such as a 400 from request parsing or a 500
   raised in a hook, come back as HTML. That breaks the §6 envelope contract for any client parsing
   JSON.

Also in `@endpoint`: a `return` inside `finally` (`server/endpoint.py:51-54`) swallows even
`BaseException` (`SystemExit`, `KeyboardInterrupt`), so a worker shutdown can be turned into an
HTTP response.

## Why it was deferred

Found during the roadmap evidence sweep. **Pre-existing.** These are separable from the redesign
entries and small enough to land early.

## Outcome / vision

Every malformed-credential path answers 403 per §5. Status codes match their HTTP meaning. Every
error response, wherever it is raised, carries the §6 envelope. Process-control exceptions
propagate.

## Sketch of the acceptance criteria

- **R1** — WHEN an `@authenticated` route receives a bearer token that is not a well-formed token,
  `refitt-server` SHALL respond 403 with the error envelope.
- **R2** — WHEN a GET route receives an invalid query parameter value, it SHALL respond 400 with the
  error envelope.
- **R3** — WHEN any HTTP error is raised outside a route body, the response SHALL be the JSON error
  envelope with the matching status.
- **R4** — WHEN a route body raises `SystemExit` or `KeyboardInterrupt`, `@endpoint` SHALL NOT
  convert it into a response.

## Notes

- `api/response.py`, `server/{app,endpoint}.py` and `route/*.py` are high-blast-radius, so every
  CONFIRMED review finding needs human sign-off.
- The SDK detects expiry by matching `status == 403 and Message == 'Token expired'`
  (`api/request.py:150-154`). Keep that message stable here; machine-readable error codes belong to
  [`api-contract-portal.md`](api-contract-portal.md).
- Update the route `info` dicts and tests in the same commit (§K6).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
