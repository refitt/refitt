# EARS — Easy Approach to Requirements Syntax

A lightweight controlled-natural-language convention for writing acceptance criteria that are
**testable and low-ambiguity**. Used by `rf-feature` to shape `GOAL.md` acceptance criteria (R-IDs).

**Nudge, don't hard-enforce.** EARS reduces ambiguity; it does not eliminate it, and forcing it onto
genuinely exploratory or ubiquitous requirements stilts them. Prefer EARS where it clarifies; fall
back to plain, unambiguous prose where EARS would be contrived. Every criterion still gets a stable
R-ID.

## Generic template

> **While** \<optional precondition/state>, **when** \<optional trigger>, the \<component> **shall**
> \<observable response>.

Keep the `<component>` a real REFITT part (the `refitt-server` `/token` route, the `Object` model,
`refitt database init`, the recommendation query, a client CLI) and the `<response>` **observable**
(an HTTP status + response envelope, a DB row state, an exit status, a printed message) so
`rf-review` can check it by driving the CLI or the API.

## The six patterns

| Pattern | Keyword | Form |
|---|---|---|
| **Ubiquitous** | *(none)* | The \<component> shall \<response>. |
| **State-driven** | `While` | While \<state>, the \<component> shall \<response>. |
| **Event-driven** | `When` | When \<trigger>, the \<component> shall \<response>. |
| **Optional-feature** | `Where` | Where \<feature is included>, the \<component> shall \<response>. |
| **Unwanted-behavior** | `If … Then` | If \<unwanted condition>, then the \<component> shall \<response>. |
| **Complex** | combo | While \<state>, when \<trigger>, the \<component> shall \<response>. |

## REFITT-flavored examples

- **R1 (event):** *When* a `GET /token` request presents HTTP Basic `key:secret` for a client whose
  stored sha256 hash matches (compared in constant time), the `refitt-server` `/token` route *shall*
  respond **200** with the success envelope `{"Status": "Success", "Response": {...}}` carrying a
  Fernet-encrypted bearer token whose `sub` is the `Client.id` (invariants §5, §6).
- **R2 (unwanted):** *If* a bearer token is missing, malformed, or expired on an `@authenticated`
  route, *then* the `refitt-server` endpoint *shall* respond **403** with an error envelope
  `{"Status": "Error", "Message": <str>}` — and reserve **401** for a valid token with insufficient
  `level` (the inverted mapping is intentional; invariants §5).
- **R3 (state):** *While* invoked against an empty database, `refitt database init` *shall* create
  every table via `metadata.create_all()` and insert the seed rows in the FK-safe `ENTITIES` order,
  exiting `0`; *when* `--test` is passed it *shall* additionally load the `refitt-assets` test seed
  (`refitt/assets/database/test/*.json`) (invariants §C2, §C3).
- **R4 (ubiquitous):** The recommendation query *shall* return only `Recommendation` rows for the
  requesting client's `Facility`/`User` scope, and *shall* declare its dialect assumption (Postgres
  `->>` is unavailable on the SQLite test site — invariant §C4) so the same code path is not silently
  broken under `temp_db.sh`.

## Anti-patterns

- Untestable adjectives ("fast", "robust", "user-friendly") — replace with an observable threshold.
- Multiple requirements in one line — split so each has its own R-ID and pass/fail.
- Specifying the *how* (implementation) in a criterion — that belongs in `PLAN.md`.
- Encoding a **suspected cause/mechanism** in a *fix's* criterion (e.g. "the fix must not use the
  broken code path") — the root cause is unverified until `/rf-plan`; state the observable broken→fixed
  behavior instead.
