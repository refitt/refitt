---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Put a serialization layer between the ORM and the API

## Problem

Routes return `Model.to_json()` directly: 53 `to_json(` calls in the server routes, 15 of them
passing `join` or `**params`. So the ORM row *is* the API contract:
- Column names (`predicted_observation_id`, `type_id`, …) go straight to the client.
- JSON blobs go out as stored; `Alert.data` is the raw broker payload.
- Datetimes are serialized with `str(datetime)` (`database/core.py:194-199`). That uses a space
  separator, and whether a timezone is present depends on the database dialect
  ([`db-dialect-parity.md`](db-dialect-parity.md)).
- Bytes become lists of base64 lines (`core.py:210-215`).
- One JSON-in-JSON field (`airmass`) is decoded ad hoc (`model.py:1434`).
- `to_json(join=True)` nesting is whatever the `relationships` dict says (§C1).

Three routes validate payloads by constructing ORM objects with `from_dict` (`route/user.py:129`,
`route/facility.py:44`, `route/recommendation.py:532`). Credential minting lives inside the model
layer (`Client.new`, `new_secret`, `new_key`, `Session.new`; `model.py:495-614`).

**The consequence:** any rename or retype in the data-model cycles is a breaking change for
`refitt-client`, the 215 message-string assertions, and any portal client, unless a
serialization layer is introduced first.

## Why it was deferred

Architectural, and **pre-existing**. It is the ordering hinge between Part III and Part IV.

## Outcome / vision

Explicit request and response schemas per resource own the wire format. ISO 8601 timestamps with an
explicit offset, documented encodings for binary and JSON fields, and validation that does not
construct ORM objects. The ORM can then change underneath without changing the API, and the schemas
can feed the OpenAPI document ([`api-contract-portal.md`](api-contract-portal.md)).

## Sketch of the acceptance criteria

- **R1** — No route SHALL serialize an ORM object directly into a response body.
- **R2** — WHEN any timestamp is returned, it SHALL be ISO 8601 with an explicit UTC offset, the
  same on both database dialects.
- **R3** — WHEN a request payload is validated, the server SHALL NOT construct an ORM object until
  validation passes.
- **R4** — WHEN a model column is renamed, the corresponding API field SHALL be unchanged unless the
  schema is deliberately versioned.

## Notes

- Shaping decisions: the schema library (pydantic is already a workspace dependency through
  refitt-host; marshmallow; hand-written dataclasses), and whether the first pass preserves today's
  field names exactly (recommended) so it can land without a client update.
- `refitt-client describe` parses the `info` dicts (`refitt/client/__init__.py:218-237`). Keep them
  consistent or migrate `describe` too.
- Related: [`model-derive-columns.md`](model-derive-columns.md),
  [`api-app-factory.md`](api-app-factory.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
