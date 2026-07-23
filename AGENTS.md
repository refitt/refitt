# AGENTS.md — REFITT engineering constitution

This file is **ground truth** for how REFITT is built. When it disagrees with the code, the
default is to **fix the code**; when a rule here is genuinely wrong, change *this file* (via
`/rf-harness`), don't route around it. `CLAUDE.md` is a symlink to this file; `.claude` is a symlink
to `.agents`.

REFITT is developed with a **spec-driven software factory** (`.agents/`). The load-bearing rules
below are mirrored, in checklist form, in `.agents/factory/invariants.md` — kept in lockstep with
this file.

---

## 1. What REFITT is

**REFITT** (Recommender Engine For Intelligent Transient Tracking) is an autonomous system that
subscribes to LSST/Rubin and other astronomical alert brokers, forecasts supernova light curves,
and generates real-time follow-up observing recommendations for a network of facilities and users.
Homepage <https://refitt.org>; docs <https://refitt.readthedocs.io>; Apache-2.0.

We are entering a from-scratch rebuild of the public portal at **refitt.org**, which drives major
work in three areas — the **data model** (SQLAlchemy/Postgres), the **testing harness** (a real
seed dataset + hermetic verify), and the **REST API + auth**. Those changes run *through* the
factory as features.

---

## 2. Workspace map

REFITT is a **uv workspace** monorepo. Everything installs into one **PEP-420 namespace package**
`refitt` (each distribution ships only its own subpackage under `src/refitt/…`; there is **no**
top-level `refitt/__init__.py` — see invariant §1).

```
[tool.uv.workspace] members = ["py/libs/*", "py/apps/*"]   exclude = ["py/apps/refitt-phot"]
```

**Libraries (`py/libs/`) — a strict dependency DAG `core → assets → data → api`:**

| Distribution   | Subpackage         | Responsibility |
|----------------|--------------------|----------------|
| `refitt-core`  | `refitt.core`      | config, logging, schema, base64, platform, exceptions, typing, profiler, ansi |
| `refitt-assets`| `refitt.assets`    | packaged asset data + loader (incl. DB seed JSON `database/{core,test}/*.json`) |
| `refitt-data`  | `refitt.database`  | SQLAlchemy models, connection/engine/session, config value objects, seed loader |
| `refitt-api`   | `refitt.api`       | crypto/token primitives, HTTP status + exception→status map, client request SDK |

**Applications (`py/apps/`) — depend downward only:**

| Distribution    | Subpackage       | CLI            | Notes |
|-----------------|------------------|----------------|-------|
| `refitt-admin`  | `refitt.admin`   | `refitt`       | administration; also owns `refitt.data.catalog` |
| `refitt-server` | `refitt.server`  | `refitt-server`| the Flask REST API (WSGI target `refitt.server:app`) |
| `refitt-client` | `refitt.client`  | `refitt-client`| lightweight client — **minimal deps only** (see §2 boundary) |
| `refitt-broker` | `refitt.broker`  | `refitt-broker`| alert-broker ingestion (Kafka/ANTARES) |
| `refitt-tns`    | `refitt.tns`     | `refitt-tns`   | Transient Name Server integration |

**Out of the workspace and out of factory scope (for now):** `py/apps/refitt-phot` (workspace-
excluded) and `py/models/*` (`refitt-ccsne-infer`, `refitt-gtf`) — these sit outside the
`py/libs/*` + `py/apps/*` globs. Revisit when they rejoin the workspace.

The root `refitt` meta-package just depends on the nine workspace distributions.

**The client boundary is an invariant (§2):** `refitt-client` must never import `refitt-data` or a
data-science dependency (numpy/scipy/pandas/sqlalchemy/astropy). Keep it installable without the
production/ML stack.

---

## 3. Architecture (enough for the invariant gate)

**Data model (`refitt.database`, in `refitt-data`).** SQLAlchemy 2.0 `Mapped`/`mapped_column` on a
legacy `declarative_base(cls=EntityMixin)`. Each table's `schema` is bound from `config` **at
class-definition time**. There is **no migration system** — schema is `create_all`/`drop_all`
only. Each model carries `columns`/`relationships` dicts **in parallel** to its mapped columns
(a dual source of truth). Seed JSON lives in `refitt-assets`, loaded in the FK-safe `ENTITIES`
order. Postgres is the production dialect (psycopg2; raw `->>`, `JSON` not `JSONB`); SQLite is
local/test only. → invariants §4, §C1–§C4.

**REST API + auth (`refitt-server` + `refitt-api`).** A **single global Flask `application`** (no
Blueprints); routes register via import side-effects. Two auth schemes: HTTP Basic key:secret
(`@authenticate`, mints tokens on `/token`) and bearer **Fernet-encrypted token** (`@authenticated`,
`sub = Client.id`, symmetric `config.api.rootkey`). Privilege is one integer `level`, **lower =
more privileged**. Secrets are sha256-hashed and compared in constant time. Status mapping is
deliberately inverted (auth-fail → 403, perm-fail → 401). Responses use a bespoke capitalized
envelope. No rate-limiting / CORS / CSRF today. → invariants §5–§7.

**Config / logging / platform (`refitt.core`).** cmdkit layered config (files + `REFITT_*` env).
Import order and fail-fast are load-bearing: `config` before `logging`; bad config →
`sys.exit(exit_status.bad_config)`; `database.connection.default_connection` built at import;
private config files must be `0600`. → invariants §4, §8.

---

## 4. Conventions

- **Commits:** subject `[category] Imperative summary`, category ∈
  `feature | fix | refactor | docs | ci | test | harness | project | release`. During a build,
  phase commits read `[category] Build {slug} P<n>: …`; they are squashed at publish.
- **No `Co-Authored-By` trailer.** REFITT commits do not carry it (this intentionally overrides
  tool defaults). Traceability lives in the committed `spec/<slug>/` record, not in trailers or
  source comments.
- **Branching / merge:** feature/fix branches off **`develop`**; squash-merge PRs into `develop`;
  promote `develop → master` on release. `master` is the release branch — features never target it.
- **Version single-source (§3, §K1):** bump every `pyproject.toml` and
  `refitt.core.__version__` together.
- **Tests (§K2):** only `@mark.unit` / `@mark.integration` are real markers (`--strict-markers`);
  use `@mark.parametrize`; tag every test. Provision a test DB with `refitt database init --test`.
- **Exit codes (§K3):** reuse `cmdkit.app.exit_status`; don't invent integer literals.
- **Comments (§K4):** declarative; no `R#`/`P#` spec-ids in source.
- **Python (§K5):** 3.12–3.13.
- **Same-commit docs (§K6):** a CLI/public-API behavior change updates the relevant Sphinx docs
  (`docs/website`) and the route `info` dict / `--help` output in the same commit.

---

## 5. The software factory

Work flows through six skills; **all durable state lives in files + git** (re-read fresh each
invocation), so builds resume and reviews run blind. Invoke as slash commands:

```
develop ─/rf-feature─▶ feature|fix/{slug}   GOAL.md              (shape: what & why, R-IDs, locked)
           ├───/rf-plan────▶  research/ PLAN.md TECH.md          (design + phased FSM; invariant gate)
           ├───/rf-build───▶  source + docs        ⟲             (execute ONE phase, verify, commit)
           ├───/rf-review──▶  REVIEW.md             ⟲             (blind adversarial QA)
           └───/rf-publish─▶  squash PR → develop                (the one irreversible step)
```

Plus **`/rf-harness`** — human-gated, the only skill that edits `.agents/` (applies the
self-improvement findings recorded in each feature's `spec/<slug>/META.md`).

- Per-feature artifacts live under `spec/<slug>/` (`GOAL.md`, `PLAN.md`, `TECH.md`, `REVIEW.md`,
  `META.md`, `research/`) and are **retained on merge** as the point-in-time design record.
- The FSM for each feature lives in `spec/<slug>/TECH.md` YAML frontmatter and is mutated **only**
  through the scripts in `.agents/factory/bin/` (run via `uv run python .agents/factory/bin/…`) —
  the scripts own the fragile YAML, the model only executes.
- Verify runs against a hermetic throwaway DB: `.agents/factory/bin/temp_db.sh` (fast SQLite site)
  or `.agents/factory/bin/temp_pg.sh` (ephemeral Postgres for server/API/integration).
- Reference material: `.agents/factory/{methodology,ears,review-rubric,invariants,portability}.md`
  and `.agents/factory/getting-started.html`.

**Environment note:** the factory (and REFITT generally) runs via `uv run`; a working workspace
env is required (`uv sync`).

---

## 6. High-blast-radius core

Any **CONFIRMED** review finding touching these requires **human sign-off before `/rf-publish`**
(mirrored in `.agents/factory/invariants.md`):

- `py/libs/refitt-data/src/refitt/database/{model,connection,core}.py`
- `py/libs/refitt-core/src/refitt/core/{config,logging,platform}.py`
- `py/libs/refitt-api/src/refitt/api/{token,response,request}.py`
- `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint,tools}.py` and `route/*.py`
