# Invariant gate & footgun checklist

An **invariant** is a design or behavioral rule a change must honor to avoid breaking the system.
This file is a curated, explicitly-enumerated subset of the load-bearing rules in the repo-root
`AGENTS.md`. **`AGENTS.md` is ground truth; this file is kept in lockstep with it** — if the two
drift, fix them together (only `/rf-harness` edits either).

## How these are enforced — two consumers

1. **`/rf-plan` — the invariant gate.** Run **before research** *and again* **after PLAN/TECH is
   drafted**. Walk only the sections a change actually touches and confirm the design honors each.
   Any deliberate bend is recorded in PLAN's **deviation-justification table**.
2. **`/rf-review` — the footgun list.** A violation of a **Tier 1** section is **auto-CRITICAL**.
   A **Tier 2** or **Tier 3** violation is **HIGH**. If a CONFIRMED finding touches a
   high-blast-radius file (below), it **forces a mandatory human sign-off gate** before publish.

**Rule:** only invoke sections **relevant to the change**. Do not manufacture findings against
untouched subsystems — a gap-hunting reviewer over-engineers.

**On the three tiers.** REFITT is mid-evolution: the data model, testing harness, and REST API are
slated for major change. **Tier 1** is what must stay true regardless. **Tier 2** captures how the
system works *today* in areas we intend to redesign — the gate surfaces them so a change doesn't
*accidentally* break them, but a change that *deliberately* redesigns one is expected: record it in
PLAN's deviation table, ship it, and `/rf-harness` retires the section. **Tier 3** is house
convention.

## High-blast-radius core

Any **CONFIRMED** review finding touching one of these requires **human sign-off before
`/rf-publish`**, regardless of the auto-loop:

- `py/libs/refitt-data/src/refitt/database/{model,connection,core}.py`
- `py/libs/refitt-core/src/refitt/core/{config,logging,platform}.py`
- `py/libs/refitt-api/src/refitt/api/{token,response,request}.py`
- `py/apps/refitt-server/src/refitt/server/{app,auth,endpoint,tools}.py` and `route/*.py`

---

## Tier 1 — Durable invariants (§1–§8 · violation = auto-CRITICAL)

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

---

## Tier 2 — Current constraints (§C1–§C4 · HIGH · honor until deliberately redesigned)

These describe how REFITT works **today** in areas targeted for overhaul. Honor them so a change
doesn't break them by accident; a change that intentionally redesigns one belongs in PLAN's
deviation table, and `/rf-harness` retires the section once the redesign lands.

### §C1 — Schema dual source of truth
Each model keeps `columns` and `relationships` dicts **in parallel** to its `mapped_column`
definitions. Adding/renaming/removing a column requires editing **both**, or `to_json` /
`from_dict` / `to_tuple` / `__repr__` (which iterate `columns`) silently break.
*Target: eliminate the duplication (derive from the mapper).*

### §C2 — No migrations
Schema is created/dropped wholesale via `Entity.metadata.create_all()` / `.drop_all()`. There is
**no Alembic / migration path**. Any schema-altering change must state its data-migration/backfill
story explicitly, or declare itself a no-go on existing data.
*Target: adopt a real migration path.*

### §C3 — Seed lockstep
The `ENTITIES` insertion order in `refitt.database` encodes FK dependency order, and the seed JSON
lives in **`refitt-assets`** (`refitt/assets/database/{core,test}/*.json`). Adding or reordering a
model requires keeping the `ENTITIES` list, the asset files, and their order **in lockstep**.
*Evolves with the schema.*

### §C4 — Dialect coupling
Postgres-specific constructs leak into the ORM: `Object.from_alias` uses the raw `->>` operator;
the JSON column variant is Postgres `JSON` (not `JSONB`); the driver is **psycopg2**; tables are
schema-qualified. SQLite is supported for **local/test only** and does not honor these. When
touching queries, **declare the dialect assumption**; do not add Postgres-only SQL to a code path
expected to run on SQLite.
*Target: decide Postgres-only vs. portable, and enforce it.*

---

## Tier 3 — Project conventions (§K · HIGH)

- **§K1 Version in lockstep, same commit** — a version bump touches every `pyproject.toml` and
  `refitt/core/__init__.__version__` together (see §3).
- **§K2 Test markers** — only `@mark.unit` and `@mark.integration` are real markers; the declared
  `parameterize` marker is a decoy (use pytest's `@mark.parametrize`). `--strict-markers` is on;
  tag every new test.
- **§K3 Exit codes** — reuse `cmdkit.app.exit_status` constants; do not invent integer return codes.
- **§K4 Declarative comments** — comments explain the invariant/why on their own terms; **never**
  embed `R#`/`P#` spec-ids in source (they restart per feature and collide across branches —
  traceability lives in `spec/<slug>/`).
- **§K5 Python** — supported range is **3.12–3.13**; no 3.10/3.11 shims.
- **§K6 Same-commit docs** — a CLI or public-API behavior change updates the relevant Sphinx docs
  (`docs/website`) **and** the route `info` dict / `--help` output **in the same commit**.

---

<!-- Keep this file in lockstep with AGENTS.md. Only /rf-harness edits it. -->
