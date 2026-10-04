# Harness change log (`/rf-harness`)

The cross-job ledger of every harness self-improvement **decision** — the *act* side of the
factory's self-improvement loop. `/rf-harness` appends one entry per **applied** / **rejected**
(and notable **deferred**) finding, and **reads this file before applying** so a fix that reverts a
recent change, or repeats a previously-rejected one, is flagged to the human rather than silently
re-applied (anti-thrash memory). Findings themselves live in each feature's `spec/{slug}/META.md`;
this file is the durable record of what was *done* about them.

Entry format — one section per decision, **newest at the bottom**:

```markdown
## {YYYY-MM-DD} — {slug} {F#}: {one-line title}
`decision=applied|rejected|deferred commit={sha|—} target={file}`
- **Rationale:** what changed and why it generalizes / why rejected (overfit, stale, would-weaken-a-gate) / why deferred.
```

<!-- Decisions are appended below this line by /rf-harness. -->

## 2026-10-04 — hypershell-sync daa3f33: Steer fix acceptance criteria to observable behavior
`decision=applied commit=3511ae3 target=.agents/factory/ears.md, .agents/skills/rf-feature/SKILL.md`
- **Rationale:** Upstream port (HyperShell hsx-zsh-completion F1). A fix criterion pinned to a suspected mechanism must be reinterpreted once `/rf-plan` root-causes the bug; generalizes to any `kind: fix`.

## 2026-10-04 — hypershell-sync 20f1290: Emit the {kind} commit category
`decision=applied commit=a5b84f7 target=.agents/skills/rf-feature/SKILL.md, .agents/skills/rf-plan/SKILL.md`
- **Rationale:** Upstream port (HyperShell part-tag-to-column F1). Shape/plan commits collapsed every non-fix kind to `[feature]`; REFITT's own AGENTS.md category list (refactor, docs, test, …) is now honored.

## 2026-10-04 — hypershell-sync 1cd3aca: Research fan-out on high-blast-radius changes regardless of appetite
`decision=applied commit=182cd2a target=.agents/skills/rf-plan/SKILL.md`
- **Rationale:** Upstream port (HyperShell part-tag-to-column F2), adapted to REFITT's High-blast-radius core list. Nearly every Part III/IV roadmap cycle touches that list.

## 2026-10-04 — hypershell-sync bee25a8+ee5442d: Add the issues/ + ROADMAP.md deferral convention
`decision=applied commit=3960aab target=.agents/factory/templates/ISSUE.md, AGENTS.md, .agents/factory/methodology.md, .gitignore`
- **Rationale:** Upstream port. Deferred code work had no home (META.md is harness feedback only). Adapted: the gitignored `.security/` lane is explicitly required because this repository is public; `.local/` gitignored for maintainer notes.

## 2026-10-04 — hypershell-sync ee5442d: Add /rf-roadmap
`decision=applied commit=792be06 target=.agents/skills/rf-roadmap/SKILL.md, AGENTS.md, .agents/factory/methodology.md, .agents/factory/getting-started.html`
- **Rationale:** Upstream port. Without retirement, ROADMAP.md grows monotonically and advertises shipped work. Adapted product-source paths (`py/**`), the numbered hidden-lane shape (REFITT's `.security/ROADMAP.md` is new), and a `git rm` fallback where `del` is unavailable.

## 2026-10-04 — hypershell-sync 222075b: Wire the deferral mechanic through feature, review and publish
`decision=applied commit=af0d00d target=.agents/skills/rf-{feature,review,publish}/SKILL.md, .agents/factory/review-rubric.md, .agents/factory/templates/GOAL.md`
- **Rationale:** Upstream port. Added one REFITT-specific sentence to rf-feature's promotion step: seeds cite `file:line` evidence that drifts, so re-check citations at promotion.

## 2026-10-04 — hypershell-sync 8d04038: Port /hs-release as /rf-release
`decision=deferred commit=— target=.agents/skills/rf-release/SKILL.md`
- **Rationale:** hs-release encodes HyperShell's proven single-version, man-page release flow; REFITT's (11 lockstep distributions, `__version__`, PyPI project creation, ghcr + Apptainer) has never run. Author it from the first modern release's actual procedure (ROADMAP: `issues/first-modern-release.md`). Maintainer-confirmed deferral.

## 2026-10-04 — roadmap-planning: PR-intake flow (conform a contributor PR before merging)
`decision=deferred commit=— target=.agents/skills/rf-feature/SKILL.md (likely a --from-pr mode)`
- **Rationale:** Maintainer wants contributor PRs checked out and conformed before merge (refitt-host #24 was merged as-is by explicit exception). Design when Braden's refitt-gtf PR opens, against a real case; open point: preserving contributor authorship alongside the no-`Co-Authored-By` convention. ROADMAP Part II depends on it.

## 2026-10-04 — roadmap-planning: Harden temp_db.sh / temp_pg.sh
`decision=deferred commit=— target=.agents/factory/bin/temp_db.sh, .agents/factory/bin/temp_pg.sh`
- **Rationale:** Evidence sweep showed the SQLite tier cannot run unattended (init always prompts on SQLite; user-config conflict at `database/core.py:100-101`; `cd "$site"` breaks relative test paths) and the Postgres tier leaks developer config (`rootkey_eval`), lacks PGTZ, binds 0.0.0.0, uses fixed ports, and probes readiness weakly. Must land before the test-suite-repair cycle (its verify substrate). Full list: `issues/test-suite-repair.md` Notes.

## 2026-10-04 — roadmap-planning: Constitution corrections from the evidence sweep
`decision=deferred commit=— target=AGENTS.md, .agents/factory/invariants.md, .agents/factory/ears.md, .agents/factory/methodology.md`
- **Rationale:** (1) workspace map omits `refitt-host`; (2) stated DAG `core → assets → data → api` is inverted for data/api (`refitt-data` imports `refitt-api`, `model.py:40`); (3) the "Postgres-only `->>`" premise is stale for SQLite ≥ 3.38; (4) `ears.md` says `--test` "additionally" loads the test seed (the flags are mutually exclusive). Apply with the cycles that settle each fact (refitt-host-conform, workspace-install-hygiene, db-dialect-parity, core-seed-incomplete) rather than ahead of them.
