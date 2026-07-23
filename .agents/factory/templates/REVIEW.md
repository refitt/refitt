# REVIEW — {Title}

> Adversarial QA by `rf-review`, run in an isolated/clean context. The correctness pass grades the
> branch diff against [`GOAL.md`](GOAL.md) + the AGENTS.md invariants **only** — it does not see
> `PLAN.md`/`TECH.md` (avoids grading-its-own-homework / plan-sycophancy). Every finding cites an
> **executed** command, not an assertion.

- **Reviewed commit:** {sha}  ·  **Base:** {base}  ·  **Date:** {YYYY-MM-DD}
- **Verdict:** approved | changes-requested
- **Cycle:** {n} of ≤3 — mirrors `review.cycle` in `TECH.md` (escalate to human on non-convergence)

## Verification run

Commands actually executed and their outcomes (the spine of the review). Pick the tier that matches
the change: `temp_db.sh` (fast throwaway SQLite; core/data/most model unit phases — cannot run
Postgres-only SQL, the `->>` operator, or the live server/API) or `temp_pg.sh` (ephemeral Postgres;
server/API/broker/integration phases — prefix `REFITT_TEMP_WITH_SERVER=1` to also launch
`refitt-server`):

- `.agents/factory/bin/temp_db.sh sh -c "uv run pytest -m unit tests/test_database"` → <result>
- `REFITT_TEMP_WITH_SERVER=1 .agents/factory/bin/temp_pg.sh sh -c "uv run pytest tests/test_web"` → <observed behavior>
- <docs build / relevant product CLI drive (`refitt`, `refitt-server`, `refitt-client`, `refitt-broker`, `refitt-tns`) when applicable>

## Requirement → evidence matrix

Bidirectional traceability. Flag requirements with no implementing change **and** changes that map
to no requirement (scope creep).

| R-ID | Implemented by (file/commit) | Verified how | Status |
|------|------------------------------|--------------|--------|
| R1   | <…>                          | <command>    | ✅ / ❌ |

Unmapped changes (possible scope creep): <list or "none">.

## Findings

Severity: **CRITICAL** (any Tier 1 §1–§8 invariant violation is auto-CRITICAL) · **HIGH** (Tier 2
§C1–§C4 or Tier 3 §K violation) · **MEDIUM** · **LOW**. Verdict: **CONFIRMED** (reproduced) vs
**PLAUSIBLE** (suspected, needs human triage). Only CONFIRMED findings auto-loop to `rf-build`.

### [CRITICAL/CONFIRMED] <one-line defect>
- **Where:** `file:line`
- **Failure scenario:** <concrete inputs/state → wrong output/crash>
- **Evidence:** <the command run and what it showed>
- **Touches invariant / requirement:** <R-ID or "invariants.md §N">

## Human-gate triggers

Set if any CONFIRMED finding touches the high-blast-radius core or a security/DB-lifecycle
invariant — these **always** require human sign-off before `rf-publish`, regardless of auto-loop.
High-blast-radius core (see AGENTS.md §6 / `invariants.md`):

- `py/libs/refitt-data/src/refitt/database/{model,connection,core}.py`
- `py/libs/refitt-core/src/refitt/core/{config,logging,platform}.py`
- `py/libs/refitt-api/src/refitt/api/{token,response,request}.py`
- `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint,tools}.py` and `route/*.py`

Security/DB-lifecycle invariants to watch: auth posture (`invariants.md` §5), response envelope &
request contract (§6), DB session lifecycle (§7), private-file permissions (§8).

- <triggered? which finding?>

## Optional completeness sub-pass (separate reviewer; may see TECH.md)

- Was every planned phase actually shipped? Did scope balloon beyond the appetite? <notes>
