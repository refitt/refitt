# Review rubric — `/rf-review`

The operating manual for the adversarial QA pass. The correctness reviewer runs in an **isolated
context** (fresh subagent) and grades the branch diff against `GOAL.md` + the AGENTS.md invariants
**only** — it is denied `PLAN.md`/`TECH.md` (showing the author's own rationale triggers
grading-its-own-homework and plan-sycophancy). Verification is by **executed command**, never by
assertion.

## What the reviewer sees

- ✅ `GOAL.md` (the locked contract — R-IDs)
- ✅ the branch diff **excluding `spec/`** (`git diff develop...HEAD -- . ':(exclude)spec/'` — the
  spec artifacts are committed on the branch, so an unfiltered diff would hand the reviewer
  PLAN/TECH/research and any prior cycle's REVIEW.md) and the full runnable repo
- ✅ [`invariants.md`](invariants.md) (the footgun checklist) and `AGENTS.md`
- ❌ **NOT** `PLAN.md`, `TECH.md`, `research/`, or `META.md` (for the correctness pass — `META.md` is
  the harness self-improvement log and leaks author intent, same as PLAN/TECH)
- A **separate, later** completeness sub-pass *may* read `TECH.md` to ask "was every planned phase
  shipped? did scope balloon?" — kept isolated so the plan never contaminates the correctness verdict.

**The `spec/` exclusion bounds the artifacts, not the rationale.** `issues/{slug}.md` and
`ROADMAP.md` sit outside `spec/`, so a seed this cycle filed is **inside** the graded diff — and it
should be. It is a claim about the repository, not a design rationale: grade it as prose the same
way you grade a docs change. Does its `Problem` describe behavior that is actually there, at the
`file:line` it cites? Does its `status:` match reality? Does the `ROADMAP.md` entry point at a file
that exists? A seed that misstates the defect is a real finding. What you must **not** do is treat
the seed as evidence of what the cycle intended — that is the leak the `spec/` exclusion exists to
prevent, and a deferral's stated reason is exactly the kind of author intent that would bias you.

## Scope — flag ONLY

1. **Correctness bugs** — the code produces wrong behavior / crashes / data corruption.
2. **GOAL-requirement gaps** — an R-ID with no implementing change, or implemented incorrectly.
3. **AGENTS.md invariant violations** — Tier 1 = auto-CRITICAL (see below).
4. **Scope creep** — changes that map to no R-ID (report, don't necessarily block).

**Do NOT** report style nits, speculative hardening, or "you could also…" gold-plating. A
gap-hunting reviewer manufactures gaps, which drives over-engineering. Silence on a clean diff is a
valid, valuable result.

## Reviewer conduct (the subagent)

- **Leave the tree clean.** Make no edits to tracked files; if you must instrument to reproduce a
  finding (a probe, a print), revert it before returning — `git status --porcelain` must be empty
  when you hand back. Drive the CLIs in a throwaway site — `.agents/factory/bin/temp_db.sh` (fast
  SQLite; core/data/most model phases) or `.agents/factory/bin/temp_pg.sh` (ephemeral Postgres;
  server/API/broker/integration phases) — never the developer's real config or database.
- The **Verdict & loop** section below is the *orchestrator's* job, executed after you return — do
  not write `REVIEW.md`, call `ReportFindings`, or run `set_phase.py` yourself. Your deliverable is
  the structured findings list + requirement→evidence matrix you were asked for.

## Refutation protocol (mandatory)

For every candidate finding, **try to disprove it first**:

1. Reproduce it — run the exact command / construct the exact input that triggers it.
2. If reproduced with observed wrong behavior → **CONFIRMED**.
3. If plausible by reading but not reproduced → **PLAUSIBLE** (needs human triage; does not auto-loop).
4. If it dissolves under scrutiny → drop it silently.

Default to dropping when uncertain. A single-model reviewer has self-preference bias even in a fresh
context, so lean on *executed evidence*, not opinion.

Because the substrate is two-tier, pick the right one when reproducing: a `->>`/JSON-operator query,
a schema-qualified table, or the live server/API cannot be exercised on SQLite (`temp_db.sh`) — use
`temp_pg.sh` (prefix `REFITT_TEMP_WITH_SERVER=1` to also launch `refitt-server`). Don't record a
finding as merely PLAUSIBLE because the *wrong* tier failed to reproduce it.

Examples of tier choice:

- data-model unit behavior — `.agents/factory/bin/temp_db.sh sh -c "uv run pytest -m unit tests/test_database"`
- an endpoint / auth path — `REFITT_TEMP_WITH_SERVER=1 .agents/factory/bin/temp_pg.sh sh -c "uv run pytest tests/test_web"`

## Severity

| Severity | Meaning |
|---|---|
| **CRITICAL** | Data loss/corruption, security/auth weakening, or **any Tier 1** AGENTS.md invariant violation (`invariants.md` §1–§8). A **Tier 2** (§C1–§C4) or **Tier 3** (§K) violation is **HIGH**, not auto-CRITICAL. |
| **HIGH** | A GOAL R-ID unmet or wrong; a real bug on a common path; a Tier 2/Tier 3 invariant violation. |
| **MEDIUM** | A bug on an edge path; a partial/again-fragile requirement. |
| **LOW** | Minor correctness risk; missing-but-non-blocking test coverage of an R-ID. |

## Verdict & loop (orchestrator only)

- Emit findings via `ReportFindings` (most-severe first) **and** write `REVIEW.md`.
- **CONFIRMED** findings → set `TECH.md` `status: blocked` + `review.verdict: changes-requested`
  (via `set_phase.py`) and loop back to `/rf-build`.
- **One exception — deferred, not blocked.** A CONFIRMED finding against behavior that **predates
  the diff** *and* that a `GOAL.md` criterion requires preserving, which cannot be repaired this
  cycle without failing that criterion. Record it in `REVIEW.md` and defer it to `issues/{slug}.md`
  (from `templates/ISSUE.md`, `status: unshaped`) plus a `ROADMAP.md` entry, committed *before* the
  `set_phase.py --reviewed-commit` call and with that call re-pinned to a fresh `git rev-parse HEAD`
  — both paths sit outside `spec/`, so a seed committed after the pinned SHA is what
  `/rf-publish`'s staleness gate reads as post-review drift. The verdict is otherwise unchanged by
  it. **If either condition fails, it blocks.** A finding that describes an unremediated weakness
  takes the `.security/` lane instead, which is gitignored — nothing to commit, and it is never
  named in the PR body.
- **PLAUSIBLE** findings → surface to the human for triage, do not auto-loop.
- Clean pass → `review.verdict: approved`; proceed to `/rf-publish`.
- Cycle 2+ **appends** a dated `## Review cycle {n}` section to `REVIEW.md` — never overwrite an
  earlier cycle; the file is the cumulative record.
- **Bounded loop:** at most 2–3 review↔build cycles — graded against the durable `review.cycle`
  counter in `TECH.md` (auto-incremented by each `set_phase.py --verdict`). On non-convergence, STOP
  and escalate to the human (self-correction does not reliably converge).

## Mandatory human sign-off gate

Regardless of auto-loop, a human must approve before `/rf-publish` whenever a CONFIRMED finding
touches:

- the high-blast-radius core (see `invariants.md`):
  - `py/libs/refitt-data/src/refitt/database/{model,connection,core}.py`
  - `py/libs/refitt-core/src/refitt/core/{config,logging,platform}.py`
  - `py/libs/refitt-api/src/refitt/api/{token,response,request}.py`
  - `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint,tools}.py` and `route/*.py`
- **or** a security / DB-lifecycle invariant — auth posture (§5: sha256+constant-time secrets,
  Fernet-encrypted bearer token, `level` lower = more privileged, the inverted 403/401 mapping, the
  known session-revocation gap), DB session lifecycle (§7: `after_request` closing `db.read` for
  `GET` vs `db.write` otherwise), or the schema constraints (§C1 dual-source `columns`/`relationships`,
  §C2 `create_all`/`drop_all` with no migration path — any schema-altering change must state its
  data-migration/backfill story).

## Optional debate variant (high-risk diffs)

For a diff touching the coupled core, run **two** independent fresh reviewers — one arguing "ship",
one arguing "block" — and reconcile. Independent instances beat single-model introspection. Reserve
for genuinely high-risk changes (cost).
