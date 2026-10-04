---
status: unshaped
kind: feature
appetite: big
lane: public
---

# Give the API a contract a browser client can be built against

## Problem

A browser portal at refitt.org cannot be built against today's API:

- **Message text is the only error contract.**
  - `@endpoint` sets `Message = str(error)` and picks the status from `RESPONSE_MAP` by insertion
    order (`server/endpoint.py:41-50`).
  - There are no machine-readable codes. The Python SDK detects expiry by matching
    `status == 403 and Message == 'Token expired'` (`api/request.py:150-154`).
  - The tests assert 215 exact message strings.
  - `ClientInvalid` and `ClientInsufficient` are defined but never used (`api/response.py:96-101`).
  - 401/403 responses carry no `WWW-Authenticate` header. Browser and SDK refresh interceptors are
    typically keyed on 401, and §5 deliberately inverts 401/403.
- **No pagination, filtering or sorting conventions.**
  - Only `/epoch` takes `offset` (`model.py:913-927`).
  - There are no cursors, totals, `Link` headers, or sort parameters.
  - `/observation` filters in Python *after* the query (`route/observation.py:77-88`), so `limit`
    is not a page size.
- **Query values are coerced heuristically.**
  - `refitt.core.typing.coerce` (`core/typing.py:29-54`) tries ISO datetime first, then int, float,
    null and booleans, so `?alias=20231010` becomes a datetime.
  - `isinstance(True, int)` lets `limit=true` pass integer checks; only `route/model.py:69-70`
    guards it.
- **No schema or docs.** The bespoke `info` dicts (66 literal entries plus 21 generated
  `/recommendation/<id>/<relation>` entries) are the only API description, and they sit behind auth
  (`route/__init__.py:36-52`). There is no OpenAPI, so no client can be generated.
- **No versioning.** No `/v1` prefix and no version header.
- **No CORS** (AGENTS.md §3). There are no `Access-Control-*` headers, so `refitt.org` →
  `api.refitt.org` calls are blocked by the browser.
- **The SDK cannot serve a browser.** `refitt.api.request` is Python-only, keeps credentials in
  module globals (`KEY`, `SECRET`, `TOKEN`; lines 80-82), is interactive, and matches
  `Content-Type` exactly (lines 184-191, 242).

## Why it was deferred

It changes the §6 envelope contract (a Tier 1 amendment) and depends on the serialization layer and
the app factory. **Pre-existing.**

## Outcome / vision

A versioned API with:
- a stable error schema carrying machine-readable codes alongside human messages;
- one pagination, filtering and sorting convention across list endpoints;
- strict, declared parameter types;
- an OpenAPI document generated from the same schemas the server validates with;
- CORS configured for the portal's origins.

The Python SDK keeps working throughout the transition.

## Sketch of the acceptance criteria

- **R1** — Every error response SHALL carry a machine-readable error code in addition to the
  message.
- **R2** — WHEN a list endpoint is called without paging parameters, it SHALL return a bounded first
  page together with the information needed to fetch the next one.
- **R3** — WHEN a query parameter cannot be parsed as its declared type, the server SHALL respond 400
  naming the parameter.
- **R4** — An OpenAPI document SHALL describe every route, and CI SHALL fail when the document and
  the routes disagree.
- **R5** — WHEN a browser on a configured portal origin calls the API, the CORS preflight SHALL
  succeed. WHEN the origin is not configured, it SHALL be refused.
- **R6** — WHEN an existing Python SDK version calls an unversioned route during the transition, it
  SHALL behave as before.

## Notes

- Shaping will likely split this into pilot plus follow-ups: errors and pagination first, then
  OpenAPI and versioning, then CORS once the auth design lands.
- Related: [`api-serialization-layer.md`](api-serialization-layer.md),
  [`api-app-factory.md`](api-app-factory.md),
  [`portal-auth-sessions.md`](portal-auth-sessions.md),
  [`docs-site-scaffold.md`](docs-site-scaffold.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
