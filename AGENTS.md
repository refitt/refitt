# AGENTS.md — REFITT engineering constitution

This file is **ground truth** for how REFITT is built. When it disagrees with the code, the
default is to **fix the code**; when a rule here is genuinely wrong, change *this file* (a
`[harness]` commit, under a human gate), don't route around it. `CLAUDE.md` is a symlink to this
file.

REFITT is developed with a **spec-driven software factory** (§ Factory). The load-bearing rules
are in § Invariants, and nowhere else.

---

## What REFITT is

**REFITT** (Recommender Engine For Intelligent Transient Tracking) is an autonomous system that
subscribes to LSST/Rubin and other astronomical alert brokers, forecasts supernova light curves,
and generates real-time follow-up observing recommendations for a network of facilities and users.
Homepage <https://refitt.org>; docs <https://refitt.readthedocs.io>; Apache-2.0.

We are entering a from-scratch rebuild of the public portal at **refitt.org**, which drives major
work in three areas — the **data model** (SQLAlchemy/Postgres), the **testing harness** (a real
seed dataset + hermetic verify), and the **REST API + auth**. Those changes run *through* the
factory as features.

---

## Workspace map

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

## Architecture (enough for the invariant gate)

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

## Conventions

- **Commits:** subject `[category] Imperative summary`, category ∈
  `feature | fix | refactor | docs | ci | test | harness | project | release`. During a build,
  phase commits read `[category] Build {slug} P<n>: …`; they are squashed at publish. `[harness]`
  is a change to § Factory or § Invariants.
- **No `Co-Authored-By` trailer.** REFITT commits do not carry it (this intentionally overrides
  tool defaults). Traceability lives in the committed `spec/<slug>/` record, not in trailers or
  source comments.
- **Branching / merge:** feature/fix branches off **`develop`**; squash-merge PRs into `develop`;
  promote `develop → master` on release. `master` is the release branch — features never target it.
- Version, tests, exit codes, comments, Python range and same-commit docs: § Invariants →
  Conventions, §K1–§K6.

---

## Factory

This repo is built by the spec-driven factory: GOAL → PLAN/TECH → build → blind review → publish.
The method and the skills live in the operator's KB (its agentic-engineering method and the `code-*`
skills, invoked as `code refitt <verb>`), and none of it is committed here; a local copy is
gitignored. The cycle's records live here: `spec/{slug}/` for work in flight, `issues/` and
`ROADMAP.md` for deferred work. Per-feature artifacts under `spec/<slug>/` (`GOAL.md`, `PLAN.md`,
`TECH.md`, `REVIEW.md`, `research/`) are **retained on merge** as the point-in-time design record.
Inside this repo, its own rules win.

**Environment note:** the factory (and REFITT generally) runs via `uv run`; a working workspace
env is required (`uv sync`).

### Profile

| Key | Value |
|---|---|
| base | `develop`, the branch every cycle starts from and lands on. `master` is the release branch only |
| branches | `{kind}/{slug}`: `feature/`, `fix/`, `refactor/`, `docs/`, `test/`, `ci/`, the prefix per GOAL `kind`; the set is open |
| commit categories | `[feature] [fix] [refactor] [docs] [ci] [test] [harness] [project] [release]` (§ Conventions). Branch commits take the GOAL's `kind` verbatim (an open set); landing subjects use these categories |
| branch commits | `[{kind}] Build {slug} P<n>: …`, with no trailer (§ Conventions) |
| landing | `squash-pr`: a PR into `develop`, squashed on merge. The maintainer merges |
| ci | `gh pr checks` must be green before landing. `tests.yml` runs on every PR into `develop` (the test matrix, the client boundary, package metadata); `docker.yml` builds the image on a PR that touches it. Until ROADMAP Part I turns `develop` green, a cycle's PR names each check it expects red and why, and any other red is a stop |
| setup | `uv sync --all-packages`: needs the native libraries `libpq` and `librdkafka` (see `Makefile`) |
| verify | `REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh uv run pytest -v && make client-boundary metadata`: the full gate, mirroring `tests.yml`. Assert the reported pass count, not the exit code. Phases narrow it (`tools/temp_db.sh` for a fast SQLite drive where §C4 allows); publish and release run all of it |
| throwaway environment | `tools/temp_db.sh <cmd…>` (fast SQLite tier) and `tools/temp_pg.sh <cmd…>` (faithful Postgres tier); contract below |
| coupled core | `py/libs/refitt-data/src/refitt/database/{__init__,model,connection,core}.py` with `py/libs/refitt-assets/src/refitt/assets/database/`; `py/libs/refitt-core/src/refitt/core/{__init__,config,logging}.py`; `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint}.py` with `route/__init__.py`; `py/libs/refitt-api/src/refitt/api/{token,response}.py` |
| same-commit rules | see § Invariants → Conventions |
| high-blast-radius paths | see § Invariants |
| security lane | on: undisclosed security findings go to gitignored `.security/`, never `issues/` |
| release | see Release recipe (`release.trigger`) |

### Release recipe

```yaml
release:
  trigger: on-demand
  version:
    source: pyproject.toml project.version
    scheme: pep440
    tag_format: "{v}"
    prerelease_syntax: '(a|b|rc)[0-9]+$|\.dev[0-9]+$'
    propose_next: none
  bump:
    lock: uv lock
    lockstep: []
    files:
      - pyproject.toml
      - py/libs/refitt-core/pyproject.toml
      - py/libs/refitt-assets/pyproject.toml
      - py/libs/refitt-data/pyproject.toml
      - py/libs/refitt-api/pyproject.toml
      - py/apps/refitt-admin/pyproject.toml
      - py/apps/refitt-server/pyproject.toml
      - py/apps/refitt-client/pyproject.toml
      - py/apps/refitt-broker/pyproject.toml
      - py/apps/refitt-tns/pyproject.toml
      - py/libs/refitt-core/src/refitt/core/__init__.py
      - uv.lock
    diff_rule: only the version string in each listed file and the workspace members' own uv.lock entries change (§K1)
    subject: "[release] Version {v}"
  gate:
    - uv sync --all-packages
    - REFITT_TEMP_WITH_SERVER=1 tools/temp_pg.sh uv run pytest -v
    - make client-boundary
    - make metadata
  tag:
    message: "Release {v}"
    signed: true
  notes: git-log-by-category
  modes:
    release:
      base: develop
      prerelease: forbidden
      final: true
      inputs: []
      work_branch: release/{v}
      branch_ops: []
      merge_into: master
      tag_on: merge
      back_merge_into: develop
      push: [master, develop, "{v}"]
      publish: gh release create {v} --verify-tag
  post_verify:
    - gh run list --workflow publish.yml --limit 1
    - gh run list --workflow docker.yml --limit 1
  caveats:
    never-run: drafted at adoption (2026-11-09) from the repository's history and workflows; the first modern release (ROADMAP Part I) validates and corrects it
    version-drift: the root says 0.27.0 and the members 0.26.1; the first modern release settles one version (§3)
    refitt-host: keeps its own version and is not bumped here
    publish: a published GitHub release fires publish.yml (PyPI, every distribution) and docker.yml (ghcr)
  clean_paths: [dist/, build/, .venv-client/, refitt.sif]
```

### Throwaway environment

`tools/temp_db.sh <cmd…>` and `tools/temp_pg.sh <cmd…>` run `<cmd…>` against a disposable instance
of the app. Each:

1. runs from the repo or worktree root;
2. creates a fresh state directory and removes it on every exit path;
3. redirects all app state (database, config, index, logs, keys) into that directory, so real data is never touched;
4. runs the command inside it, so relative writes can't reach the worktree;
5. exercises the current tree: rebuild or run from source, never a stale binary;
6. pins tool discovery back to the repo;
7. writes its own output to stderr and passes the command's exit status through.

Here that means a throwaway database seeded with `refitt database init --test`, forced through
`REFITT_*` environment variables, and `UV_PROJECT` pointing back at the repo. `temp_db.sh` is the
fast SQLite tier and does not exercise Postgres-only SQL (§C4). `temp_pg.sh` is the faithful tier:
an ephemeral `postgres:16` container, or a scratch database with `REFITT_TEST_PG=1`, plus the dev
server with `REFITT_TEMP_WITH_SERVER=1`. **Both fall short of items 3 and 2 today.** A developer's
`~/.refitt` config leaks in, and `temp_db.sh` prompts on SQLite. The fix is
`issues/verify-helpers-harden.md`, which must land before the test-suite cycle.

### Where deferred work goes

A pass that decides *not* to fix something still records it, and the destination is not a matter
of taste:

| Home | Holds | Written by |
|---|---|---|
| `issues/{slug}.md` | **Deferred code work**, pre-shaped from the KB's ISSUE template, `status: unshaped` | whoever defers it |
| `ROADMAP.md` | the **ordered index** — one entry per issue, `**Seed:**` pointing at the `issues/` file | whoever defers it |
| `.security/issues/{slug}.md` + `.security/ROADMAP.md` | the same two things for **unremediated security findings** — gitignored, never published | whoever defers it |
| `spec/{slug}/` | work **actually in flight** | the lifecycle skills |
| the KB inbox | **Harness/skill feedback only** — "was this the *factory's* fault", as `friction` lines. Never code follow-ups. | the lifecycle skills |

An `issues/{slug}.md` is a *candidate, not a contract*: `code refitt feature` promotes it into
`spec/{slug}/GOAL.md`, and that promotion is where appetite, non-goals and the R-IDs get
negotiated with a human. **Never copy one into a `GOAL.md` verbatim** — `code refitt review` grades
a GOAL, and a proposal nobody accepted is not a contract. The `status:` field is the guard:
`unshaped` (raw deferral — evidence captured, nothing agreed), `shaped` (already negotiated with a
human, but **not yet accepted into a cycle**), `adopted:{slug}` (promoted; `spec/{slug}/` owns it
now, and the record stays *while the cycle is in flight* so the ROADMAP index does not dangle). Two
further values close a deferral **without** shipping — `declined` and `accepted-behaviour` — and
those are terminal records, indexed under `ROADMAP.md` § *Settled questions* rather than as cycles.

**A deferral is retired, not kept forever.** When the cycle that adopted a seed lands on `develop`,
`code refitt roadmap` deletes the seed and removes its `ROADMAP.md` entry: `spec/{slug}/` is the
retained account and git history holds the file. Retire only on evidence the cycle *landed* — an
`adopted:{slug}` marker proves a cycle started, never that it finished. The security lane inverts
this: nothing under `.security/` is ever deleted, because it is gitignored and a deletion there
leaves no history to recover from, so a remediated finding keeps its file, its closure is recorded
in `.security/STATUS.md`, and its `.security/ROADMAP.md` entry moves out of the ordered queue.

**The security lane is not optional.** This repository is public. A deferral that describes an
*unremediated* weakness — a live exploitable mechanism, an attack path, a leaked credential, or
enough evidence to reconstruct one — goes in `.security/`, which is gitignored along with `.local/`
(maintainer-local notes). Publishing a standing roadmap of live vulnerabilities hands an attacker a
work plan. The *fixes* land as ordinary public commits and PRs when they ship; only the inventory
of what is still open stays private. Architectural facts this file already states (e.g. "no
rate-limiting / CORS / CSRF today") are not secrets and may appear in public seeds. When in doubt
which lane an item belongs to, use `.security/` and ask.

This coexists with the **GitHub tracker**: a GH issue is the public-facing ticket,
`issues/{slug}.md` is the pre-shaped spec behind it, and the two may link to each other. Neither
replaces the other.

---

## Invariants

The gate for every plan and the footgun list for every review. A plan walks only the sections its
change touches, **before research and again after PLAN/TECH is drafted**, and records any deliberate
bend in PLAN's deviation-justification table. A review grades every violation of a numbered section
(§1–§8) as CRITICAL; a violation of § Current constraints (§C1–§C4) or § Conventions (§K1–§K6) is
HIGH. **Only invoke sections relevant to the change.** Do not manufacture findings against untouched
subsystems — a gap-hunting reviewer over-engineers.

**On the three tiers.** REFITT is mid-evolution: the data model, testing harness, and REST API are
slated for major change. The numbered sections are what must stay true regardless. § Current
constraints captures how the system works *today* in areas we intend to redesign — the gate surfaces
them so a change doesn't *accidentally* break them, but a change that *deliberately* redesigns one is
expected: record it in PLAN's deviation table, ship it, and retire the section here in the same
cycle. § Conventions is house convention.

### High-blast-radius paths (human gate)

A CONFIRMED finding in any of these files needs a human decision before the cycle lands; a plan
touching one always runs research. The list only widens: when code moves, add the new home and never
remove the old entry. Skills and templates cite this list and never copy it.

- `py/libs/refitt-data/src/refitt/database/{model,connection,core}.py`
- `py/libs/refitt-core/src/refitt/core/{config,logging,platform}.py`
- `py/libs/refitt-api/src/refitt/api/{token,response,request}.py`
- `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint,tools}.py` and `route/*.py`

### §1 — Namespace-package integrity

REFITT is a single **PEP-420 namespace package** `refitt`, assembled from every workspace distro's
`src/refitt/<subpkg>/`. **No distribution may ship a top-level `refitt/__init__.py`** — a stray
top-level `__init__.py` collapses the namespace merge and hides the other packages. Each distro
ships only its own subpackage(s) under `refitt/` (e.g. `refitt-core` → `refitt/core/`, `refitt-data`
→ `refitt/database/`). *Highest structural blast radius.*

### §2 — Dependency direction & the client boundary

The lib dependency DAG is `refitt-core → refitt-assets → refitt-data → refitt-api`; apps depend
downward only; **no cycles**. **`refitt-client` MUST NOT import `refitt-data`** or any data-science
dependency (`numpy`, `scipy`, `pandas`, `sqlalchemy`, `astropy`, …). Its dependency set is
deliberately minimal (`refitt-core`, `refitt-api`, `cmdkit`, `requests`) so the client installs
without the production/ML stack. A change that pulls a heavier dep across this boundary is a break.

### §3 — Version single-source

There is **one authoritative version** for the project; every distribution's `pyproject.toml`
version must agree with it (and with `refitt/core/__init__.__version__`). *(Currently drifted —
root `pyproject.toml` `0.27.0` vs. the libs' `0.26.1`; the gate should flag any change that widens,
rather than closes, this gap.)*

### §4 — Import-time determinism & fail-fast

Module import order and fail-fast semantics are load-bearing:
- `refitt.core.__init__` forces `config` to load **before** `logging`.
- `core.config`, `core.logging`, and `database.connection` call `sys.exit(exit_status.bad_config)`
  on bad configuration — they fail fast, they do not limp.
- `database.model` binds each table's `schema` from `config` **at class-definition time**; changing
  when/how `schema` is resolved changes every table.
- `database.connection.default_connection` is constructed **at import**.
Preserve this ordering and the fail-fast behavior; do not defer or swallow these errors.

### §5 — Auth posture

- Client secrets are stored **sha256-hashed** and compared in **constant time** (`bytes_eq`); never
  store or compare plaintext.
- The bearer token is a **Fernet-encrypted** JSON blob (not a signed RFC-7519 JWT) with `sub =
  Client.id`, encrypted with the symmetric `config.api.rootkey`.
- Privilege is a single integer `level` where **lower = more privileged** (0 super-admin,
  1 admin, 10 default).
- The status mapping is intentional and inverted from convention: **missing/invalid/expired auth →
  403**, **insufficient permission → 401**. Do not "correct" it silently.
- **Never log or echo secrets** (config CLI, `DEBUG` logs, argv).
- The session-revocation gap (`@authenticated` validates the encrypted `exp` + `Client.valid`, not
  the `Session` row) is **known**; do not paper over it silently — changing it is a shaped feature.

### §6 — Response envelope & request contract

- Success: `{"Status": "Success", "Response": <payload>}`. Error:
  `{"Status": "Error" | "Critical", "Message": <str>}`. Keys are **capitalized**; keep the shape.
- `require_data(..., required_fields=…)` **rejects unexpected fields** (not just missing ones).
- A write `IntegrityError` is surfaced as `ConstraintViolation` → **400**.
- There is a **single global Flask `application`** (no Blueprints); routes register via import
  side-effects in `refitt.server.route`. The WSGI target is `refitt.server:app`.

### §7 — DB session lifecycle

`after_request` closes the **read** session for `GET` and the **write** session otherwise
(`db.read` vs `db.write`, keyed purely on HTTP method). Routes must use the scope matching their
method; a write under `GET` (or vice-versa) leaks or mis-scopes the session.

### §8 — Private-file permissions

Config files holding credentials must be mode **`0600`** (`check_private` / `set_private`); reading
a non-private config file raises `ConfigurationError`. Do not relax this check.

### Current constraints (§C1–§C4 · HIGH · honor until deliberately redesigned)

These describe how REFITT works **today** in areas targeted for overhaul. Honor them so a change
doesn't break them by accident; a change that intentionally redesigns one belongs in PLAN's
deviation table, and retires its section here once the redesign lands.

#### §C1 — Schema dual source of truth

Each model keeps `columns` and `relationships` dicts **in parallel** to its `mapped_column`
definitions. Adding/renaming/removing a column requires editing **both**, or `to_json` /
`from_dict` / `to_tuple` / `__repr__` (which iterate `columns`) silently break.
*Target: eliminate the duplication (derive from the mapper).*

#### §C2 — No migrations

Schema is created/dropped wholesale via `Entity.metadata.create_all()` / `.drop_all()`. There is
**no Alembic / migration path**. Any schema-altering change must state its data-migration/backfill
story explicitly, or declare itself a no-go on existing data.
*Target: adopt a real migration path.*

#### §C3 — Seed lockstep

The `ENTITIES` insertion order in `refitt.database` encodes FK dependency order, and the seed JSON
lives in **`refitt-assets`** (`refitt/assets/database/{core,test}/*.json`). Adding or reordering a
model requires keeping the `ENTITIES` list, the asset files, and their order **in lockstep**.
*Evolves with the schema.*

#### §C4 — Dialect coupling

Postgres-specific constructs leak into the ORM: `Object.from_alias` uses the raw `->>` operator;
the JSON column variant is Postgres `JSON` (not `JSONB`); the driver is **psycopg2**; tables are
schema-qualified. SQLite is supported for **local/test only** and does not honor these. When
touching queries, **declare the dialect assumption**; do not add Postgres-only SQL to a code path
expected to run on SQLite.
*Target: decide Postgres-only vs. portable, and enforce it.*

### Conventions (same-commit rules · §K · HIGH)

- **§K1 Version in lockstep, same commit** — a version bump touches every `pyproject.toml` and
  `refitt/core/__init__.__version__` together (see §3). The version lives at the release recipe's
  `version.source` and moves with the recipe's `bump.files`; the recipe's `gate` mirrors CI.
- **§K2 Test markers** — only `@mark.unit` and `@mark.integration` are real markers; the declared
  `parameterize` marker is a decoy (use pytest's `@mark.parametrize`). `--strict-markers` is on;
  tag every new test. Provision a test DB with `refitt database init --test`.
- **§K3 Exit codes** — reuse `cmdkit.app.exit_status` constants; do not invent integer return codes.
- **§K4 Declarative comments** — comments explain the invariant/why on their own terms; **never**
  embed `R#`/`P#` spec-ids in source (they restart per feature and collide across branches —
  traceability lives in `spec/<slug>/`).
- **§K5 Python** — supported range is **3.12–3.13**; no 3.10/3.11 shims.
- **§K6 Same-commit docs** — a CLI or public-API behavior change updates the relevant Sphinx docs
  (`docs/website`) **and** the route `info` dict / `--help` output **in the same commit**.
- Point to a rule; don't restate it. A rule restated in N places is a same-commit obligation in
  all N.
