# Harness portability — running the factory outside Claude Code

The `rf-*` skills are plain markdown + portable shell (`git`, `uv run`, the `.agents/factory/bin`
scripts) and are meant to run on **any** agent harness — Claude Code, Warp, OpenCode, etc., including
**open-weight models**. A handful of affordances are Claude-Code-specific; each has a graceful fallback
so the skill still works (at worst with one manual step) elsewhere. This table is the compatibility
contract — keep it current when a skill gains a new affordance, and every skill links here.

## Affordance → fallback

| Claude-Code affordance | What it does | Fallback on another harness |
|---|---|---|
| **Frontmatter** (`name`, `description`, `argument-hint`, `allowed-tools`, `disable-model-invocation`) | Skill discovery + least-privilege tool gating | **Harmlessly ignored** — it is YAML frontmatter, not procedure. The skill **body** is the operating manual. Grant whatever tools your harness needs by its own mechanism (the committed `.agents/settings.json` is the safe baseline of what the skills run). |
| **`` !`cmd` `` injection** under "Current state (injected at load)" | Runs shell at load, pastes the output into context | **Run those commands yourself** as the first action (pre-flight / Step 1). The listed commands *are* the state — if you see literal `` !`…` `` text, execute it and read the output. |
| **`$ARGUMENTS`** | The invocation's arguments | Use your harness's argument mechanism, or read the args from the user's message. |
| **`AskUserQuestion`** | Structured multiple-choice to the human | **Ask in plain text and STOP** for the answer. Never guess to dodge the question. |
| **`Agent` subagent fan-out** (`rf-plan` research, `rf-review` reviewer) | Parallel read-only workers | **Do the work sequentially yourself**, producing the same artifacts (`research/NN-*.md`; the review). For `rf-review` this weakens *blindness* — compensate by starting a clean context and grading strictly on executed evidence (the rubric says how). |
| **`ReportFindings`** (`rf-review`) | Renders findings in the host UI | **Additive, not load-bearing** — `REVIEW.md` is the durable record. Skip the call; still write `REVIEW.md`. |
| **`Skill` / `/rf-*` launch** | How a skill starts | Launch by your harness's mechanism; the lifecycle handoffs ("then run `/rf-plan`") are advisory prose. |

> **Scope the allowlists honestly:** the frontmatter `allowed-tools` and the committed
> `.agents/settings.json` are accident-protection, not a security boundary — `Bash(uv run *)` alone
> admits arbitrary Python (`uv run python -c …`). They exist to stop fat-fingered mutations (which
> is why `git checkout` — a silent working-tree discard — is deliberately absent), not to confine a
> determined adversary.

## Already portable — no action

`git`, `uv run …` (incl. the FSM scripts and `meta_status.py`), file read/edit/grep/glob, and every
artifact under `spec/{slug}/` and `.agents/`. All lifecycle state lives in **files** (`TECH.md`
frontmatter, `META.md`), re-read fresh each invocation — nothing relies on Claude-specific memory. The
scripts are invoked by repo-relative path (`.agents/factory/bin/…`), not a Claude-specific variable.
The two-tier verify substrate is likewise portable: `.agents/factory/bin/temp_db.sh` (fast throwaway
SQLite) and `.agents/factory/bin/temp_pg.sh` (ephemeral Postgres) are ordinary shell scripts run by
repo-relative path.

## Smaller / open-weight models

The skills deliberately assume less skill/wisdom than the author, so a weaker model **fails safe** by
following the guardrails rather than guessing: STOP-and-ask on ambiguity, `[NEEDS CLARIFICATION]`
markers, the invariant gate, blind evidence-based review, and silence-by-default meta-notes all degrade
gracefully. When adapting a skill for another harness, keep instructions imperative and checkable, and
preserve every STOP condition — they are the safety net. Friction you hit doing so is itself a
meta-note (`spec/{slug}/META.md`) for `/rf-harness` to fix.
