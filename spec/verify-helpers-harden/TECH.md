---
slug: verify-helpers-harden
title: Harden the throwaway-environment helpers
kind: test
appetite: small
status: in_progress
branch: test/verify-helpers-harden
base: develop
current_phase: P1
last_updated: '2026-11-10'
phases:
- id: P1
  name: temp_db.sh and the shared plumbing meet the contract on SQLite
  status: pending
  satisfies:
  - R1
  - R2
  - R3
  - R5
  - R6
  - R7
  - R11
  depends_on: []
  parallel: false
  hammerable: false
  hill: uphill
  verify: sh spec/verify-helpers-harden/verify/gate_temp_db.sh
- id: P2
  name: temp_pg.sh hardened; verify and release gate root-anchored
  status: pending
  satisfies:
  - R2
  - R3
  - R4
  - R5
  - R6
  - R7
  - R8
  - R9
  - R10
  - R11
  depends_on:
  - P1
  parallel: false
  hammerable: false
  hill: uphill
  verify: sh spec/verify-helpers-harden/verify/gate_temp_pg_local.sh
- id: P3
  name: Throwaway environment rewritten; scope and ledger closed
  status: pending
  satisfies:
  - R7
  - R12
  depends_on:
  - P1
  - P2
  parallel: false
  hammerable: false
  hill: uphill
  verify: sh spec/verify-helpers-harden/verify/gate_docs.sh
review:
  last_reviewed_commit: ''
  verdict: none
  blocked_reason: ''
  cycle: 0
---

# TECH.md — Harden the throwaway-environment helpers

The **context engine and finite-state machine** for building this feature. The YAML
frontmatter above is the resume ground-truth (read it from the cycle worktree with
`uv run --with pyyaml python "$KB/bin/factory/next_phase.py" spec/{slug}/TECH.md`); the per-phase
checklists below are the work. `code-build` executes the next actionable phase, runs its
`verify:` command, updates state via
`uv run --with pyyaml python "$KB/bin/factory/set_phase.py" …`, and makes one atomic code+state commit.

- **Vision / requirements (locked):** [`GOAL.md`](GOAL.md) — R-IDs are the contract.
- **Authoritative design:** [`PLAN.md`](PLAN.md).
- **Backing research:** none (lean path); the probes are in PLAN §4.

## Frontmatter field reference

- `status` (top): `planned | in_progress | blocked | in_review | done` (`done` is stamped by
  `code-publish` after confirmation, just before landing — the terminal state of the retained record)
- `appetite`: `small | big` — caps phase count and build-iteration budget (circuit breaker).
- `branch`, `base`: the cycle's branch (prefix per GOAL `kind`, from the profile's `branches`) and the
  profile's `base`.
- phase `status`: `pending | in_progress | done | blocked`
- `satisfies`: GOAL R-IDs this phase delivers (traceability anchor for `code-review`).
  **Artifact-deliverable R-IDs.** Some requirements are met by a *committed document* — a research
  audit, a protocol doc, an assessment — not by CLI-observable behaviour. Attach such an R-ID to the
  phase that produces and commits the artifact, and give that phase a content `verify:`
  (`test -f …`, a `grep -q` for the sections that must exist) rather than forcing a CLI drive.
  **Say so in the phase body**, because it changes who can grade it: `code-review` blinds its reviewer
  to all of `spec/`, so an R-ID whose evidence lives there is graded by the *orchestrator*, not the
  blind reviewer. Naming it in `TECH.md` is what lets the review skill route it correctly instead of
  reporting an unverifiable requirement.
- `depends_on`: phase ids that must be `done` first (a phase is actionable only when met).
- `parallel`: `true` only for genuinely independent, non-coupled work (docs, tests, isolated leaf
  modules). Any phase touching the profile's `coupled core` is always `false`.
- `hammerable`: `false` marks a correctness/security phase that scope-hammering must **never** cut.
- `hill`: `uphill` (still figuring it out) → `crest` (unknowns resolved) → `downhill` (just
  executing). A phase stuck `uphill` across builds is a raised hand → escalate to the human.
- `attempts`: durable failed-verify counter (absent = 0), bumped by `set_phase.py --phase P<n>
  --record-attempt` on every red verify gate; `next_phase.py` warns at ≥3 — the circuit breaker
  runs on this file, not on session memory.
- `verify`: the exact command that proves the phase (prefer driving the real CLI, not just tests —
  wrap CLI drives in the profile's `throwaway environment` helper, `<helper> sh -c "…"`, so they hit
  a disposable instance, never the developer's real data). A gate carrying `$( )` or quoting the
  calling shell would mangle is set with `set_phase.py --verify-file PATH`, not `--verify`.
- `review.cycle`: completed review passes, auto-incremented by every `set_phase.py --verdict …`;
  REVIEW.md's "Cycle {n}" mirrors it and the ≤3-cycle bound is graded against it. `--verdict approved`
  also clears `review.blocked_reason` unless one is passed explicitly.

## Conventions (apply to every phase)

- Commit conventions, code style, and load-bearing invariants come from the repo's `AGENTS.md` — it
  is the constitution. Walk the sections of its § Invariants that this change touches; that is the
  curated footgun checklist.
- One phase per `code-build` invocation by default; one atomic commit containing **both** the code and
  the `TECH.md` state change. The branch commit subject is code-build's (`$KB/skill/code-build.md` →
  Step 6), not restated here; branch commits are squashed away at `code-publish` per the profile's
  `landing`. Trailers follow the profile's `branch commits`.
- The last phase carries the standing last-phase items: the deferral ledger (`code-plan` Step 6.8),
  and every item the previous cycle's last phase carried for a project-level obligation (mpsearch's
  `## Times` quote, taken as `code-build` Step 4 says). A plan that drops one says why in `PLAN.md`.
- A PR body (when the profile's `landing` opens one) ends with an attribution naming the actual
  harness, model, and variant.
- A CLI/feature change obeys the profile's `same-commit rules` (§ Conventions in `AGENTS.md`): the
  help text, docs, or generated files it names change **in the same commit**.

**Cycle-specific rules (every phase).**

- No change under `py/` or `.github/`, and `uv.lock` stays byte-identical: run `uv` only with
  `UV_NO_SYNC=1` (or `--no-sync`) in the worktree, never `uv sync`, `uv lock` or plain `uv run`.
  Confirm `git diff --quiet -- uv.lock` before each commit.
- The gates build their own environment in a cache under `$TMPDIR` (`verify/lib.sh`); the first run
  on a host needs PyPI access. They never write in the worktree.
- Stage the phase's files before running its `verify:`: the gates read the index.
- The helpers are POSIX `sh`: check each edit with both `sh -n` and `dash -n`.
- **Container mode is never claimed locally.** R4, R8 and R10, and the container-mode half of every
  other R-ID, are proven only by `verify/container_drive.sh`, which the foreman has run on a Docker
  host before review (GOAL Clarification Q2). A phase report says which R-IDs its gate proved here.

---

## Phase P1 — temp_db.sh and the shared plumbing meet the contract on SQLite
**Satisfies:** R1, R2, R3, R5, R6, R7, R11 · **Depends on:** —
**Goal:** `tools/temp_db.sh` runs any command unattended against a fresh, isolated SQLite instance,
through a new sourced `tools/temp_common.sh` that `temp_pg.sh` will reuse.

- [ ] Write `tools/temp_common.sh` per PLAN §2: `REPO_ROOT` from the helper's location;
      `temp_preflight` (root, `/etc/refitt.toml`, missing project environment, missing `perl`);
      `temp_enter` (pin `UV_CACHE_DIR`; `mktemp -d`; scrub `REFITT_DATABASE_*`,
      `REFITT_API_ROOTKEY*` and `PG*`; export `REPO_ROOT`, `HOME`, `TMPDIR`, `UV_PROJECT`, `UV_NO_SYNC`,
      `PYTHONPYCACHEPREFIX`, `PYTEST_ADDOPTS` cache dir, database scopes; `cd`); `temp_rootkey`;
      `temp_run` (process group through `perl`, stdin on fd 3; foreground at a terminal);
      `temp_stop_group` with its 10 s KILL watchdog; the EXIT/INT/TERM traps, which ignore a
      second INT or TERM during teardown and make leftovers writable before `rm -rf`;
      `temp_docker`.
- [ ] Rewrite `tools/temp_db.sh` on it: force SQLite at `$state/refitt.db`, rootkey, pipe `y` into
      `refitt database init ${REFITT_TEMP_DB_INIT:---test}` with its stdout on stderr, run the
      command, exit with its status.
- [ ] Rewrite the header: what it does as it now behaves, the root-anchored usage line
      `tools/temp_db.sh sh -c 'uv run pytest -m unit "$REPO_ROOT/tests/test_database"'`, and the
      `init` answer with its record `issues/init-sqlite-prompt.md`. No caveat pointing at this
      cycle (R12's half for this helper).
- **Verify:** `sh spec/verify-helpers-harden/verify/gate_temp_db.sh` — exits 0 and ends
  `PASS gate_temp_db`. Measured at planning: 73 s on the P1 prototype tree with a warm gate
  environment (10 s of it the TERM-twice watchdog case).
- **Touches:** `tools/temp_common.sh` (new), `tools/temp_db.sh`.

## Phase P2 — temp_pg.sh hardened; verify and release gate root-anchored
**Satisfies:** R2, R3, R4, R5, R6, R7, R8, R9, R10, R11 · **Depends on:** P1
**Goal:** `tools/temp_pg.sh` meets the contract in both bring-up modes, and the profile's `verify`
and the release `gate` find their tests from the state directory. This phase's gate proves R9
here; everything else it lists is proven in container mode by the container drive, and in
`REFITT_TEST_PG=1` mode partly here (stubbed) and fully by the drive.

- [ ] Rewrite `tools/temp_pg.sh` on `temp_common.sh` per PLAN §2: the daemon check before anything
      is created, bounded at 10 s (message names `REFITT_TEST_PG=1`); capture of the five scratch variables in
      `REFITT_TEST_PG=1` mode; `PGTZ`; the labelled container on `127.0.0.1::5432` with
      `TZ=America/Indiana/Indianapolis`; the host-side psycopg2 readiness loop with a 60 s
      wall-clock deadline and a fast fail when the container stops; forced database variables;
      rootkey; `init --drop --test` with stdout on stderr; the dev server in its own process group on
      a free port with `REFITT_API_SITE`/`REFITT_API_PORT` exported and a 30 s HTTP readiness
      deadline, probed with proxies disabled; `temp_run`.
- [ ] Rewrite its header (R12's half for this helper), with the root-anchored usage line
      `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest "$REPO_ROOT/tests/test_web"'`.
- [ ] In the same commit, because the old lines stop finding tests once the command runs in the
      state directory: `AGENTS.md` § Factory → Profile `verify` becomes
      `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest -v "$REPO_ROOT"' && make client-boundary metadata`,
      and the release recipe's `gate` step becomes
      `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh sh -c 'uv run pytest -v "$REPO_ROOT"'`.
- **Verify:** `sh spec/verify-helpers-harden/verify/gate_temp_pg_local.sh` — exits 0 and ends
  `PASS gate_temp_pg_local`. Measured at planning: 112 s on the P2 prototype tree, about 50 s of
  it the dev-server timeout (behind a 502 proxy) and wedged-daemon cases.
- **Touches:** `tools/temp_pg.sh`, `AGENTS.md` (§ Factory → Profile, Release recipe).

## Phase P3 — Throwaway environment rewritten; scope and ledger closed
**Satisfies:** R7, R12 · **Depends on:** P1, P2
**Goal:** `AGENTS.md` § Factory → Throwaway environment describes the helpers as they now behave,
with no caveat; the cycle's scope and deferrals are closed. R12 is met by committed documents
outside `spec/` (the helper headers and `AGENTS.md`), so the blind reviewer can grade it.

- [ ] Rewrite the prose after the seven-item contract in § Throwaway environment per PLAN §2 (the
      contract list itself stays); drop "Both fall short of items 3 and 2 today" and its pointer to
      this cycle's seed.
- [ ] Re-read both helper headers against the final behaviour; fix any drift.
- [ ] Deferral ledger: walk P1 and P2's bodies and commit messages for every deferral (the phrases
      code-plan Step 6.7 lists); each needs its own seed under `issues/`, from the ISSUE template,
      and a `ROADMAP.md` entry. The one filed at planning is `issues/init-sqlite-prompt.md` (the
      SQLite `init` prompt).
- [ ] Run `sh spec/verify-helpers-harden/verify/gate_docs.sh pre-push` last, after any fix.
- **Verify:** `sh spec/verify-helpers-harden/verify/gate_docs.sh` — mode `all` runs P1's and P2's
  gates first, then this phase's own checks (`phase` mode runs only the latter; `pre-push` only
  scope and the private-path scan). Exits 0 and ends `PASS gate_docs all`. Measured at planning on
  the final prototype tree: `all` 3 min 21 s, `phase` and `pre-push` under 1 s.
- **Touches:** `AGENTS.md` (§ Factory → Throwaway environment), `tools/temp_db.sh`,
  `tools/temp_pg.sh` (headers only), `issues/`, `ROADMAP.md` (only if a new deferral appears).

---

## How `code-build` drives this

1. `next_phase.py` prints the next actionable phase (statuses are authoritative; the
   `current_phase` pointer is reconciled against them).
2. Pre-flight: the cycle worktree is clean, on `branch`, and `base` is reachable.
3. Execute every `[ ]` in the phase (consult `PLAN.md` / `research/` for detail).
4. Run the phase's `verify:` command — never advance on a checkbox alone.
5. Amend this file freely if reality diverges (regenerate frontmatter with `set_phase.py`; note the
   amendment in the commit body). STOP and escalate only on a **`GOAL.md` contradiction**.
6. Mark the phase `done`, advance `current_phase`, `--touch`; one `[{category}]` commit; stop and report.
