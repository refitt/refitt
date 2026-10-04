# REFITT Roadmap

REFITT subscribes to LSST/Rubin and other alert brokers, forecasts supernova light curves, and
generates real-time follow-up recommendations for a network of observing facilities. The driving
project now is a from-scratch rebuild of the public portal at refitt.org, which needs major work in
three areas: the data model, the test harness, and the REST API with its auth. This document records
the work still intended. It starts with the repairs that make the workspace honest enough to build
on, then lists the cycles that rebuild each layer for the portal.

This is a **forward-looking index, not an implementation plan.** Each entry states a problem and the
intent behind solving it; the *how* belongs to `/rf-plan`. As-built architecture and the
load-bearing invariants live in [`AGENTS.md`](AGENTS.md), which stays ground truth.

Each entry's **Seed** points at an [`issues/{slug}.md`](issues/) file carrying the evidence in
enough detail that a future session does not have to re-derive it. Those are **candidates, not
contracts**: `/rf-feature` promotes one into `spec/{slug}/GOAL.md`, and that promotion is where a
human negotiates appetite, non-goals, and the R-IDs `rf-review` will grade. The `status:` field on
each issue is the guard — `unshaped` (raw deferral), `shaped` (negotiated, not yet accepted into a
cycle), `adopted:{slug}` (promoted, and retired from this index by `/rf-roadmap` once the cycle lands
on `develop`). Two further values close an item **without** shipping — `declined` and
`accepted-behaviour` — and those are listed under *Settled questions* rather than as cycles. See
*Deferred work* in [`AGENTS.md`](AGENTS.md) §5 for which lane an item belongs in.

**Order is deliberate.** Part I comes first because CI is red on `develop` for reasons unrelated to
any feature, and nothing after it can be verified until that is fixed. Several entries are hard
prerequisites of later ones, not just more urgent, and each entry names its dependencies.
Horizons are indicative; the named dependencies are the hard constraints.

Every seed was written from an out-of-cycle evidence sweep of `develop` at `8e85fc8` on 2026-10-04.
They cite `file:line`, and those citations drift as code moves, so re-check them at promotion.

---

# Part I — Make the workspace honest

Every job on `develop` fails today (run 36265361934), and none of the failures come from feature
work. The lockfile predates two workspace changes, three distributions under-declare their
dependencies, the test suite still imports a module tree that no longer exists, and the docs build
points at a theme that is not installed. These five entries clear that debt, so the cycles after
them can be graded against executed evidence instead of a red baseline.

## `refitt-host` joined the workspace without conforming to it

Braden's host-galaxy association library landed (#24) as a top-level `refitt_host` package with its
own version (1.0.0), license (MIT), Python floor (3.11) and a conda environment file. It was
deliberately merged first and conformed afterwards. Two of its packaging choices now affect the
whole workspace. Its git-URL dependency blocks the PyPI upload and the git-less Docker/Apptainer
build. Its unbounded `lsdb` extra drags pandas 3 / numpy 2.5 into every member's resolution. On the
base install it also returns `no_candidates` silently when its catalog backend is missing. The
shaping conversation has real decisions to make: library or app, the subpackage name, which extras
stay, and the license.

*Horizon: now · Depends on: — · Refs: settle its dependency choices before the lock regeneration in
the next entry; coordinate the rename with Braden before his refitt-gtf PR, which may import it*
**Seed:** [`issues/refitt-host-conform.md`](issues/refitt-host-conform.md)

## A stale lock and undeclared dependencies break the install before any test runs

`uv.lock` predates `refitt-host` and fails `uv lock --check`, so every non-frozen sync re-resolves.
That pulls numpy 2.5 alongside astropy 7.0.1, which nothing declares, and the `refitt` CLI then
crashes on `np.in1d` during test-DB initialization. In the same sweep: `refitt-api` declares
SQLAlchemy for one import, which breaks the client boundary (invariant §2). It also omits
`refitt-core`, and `refitt-data` imports `refitt-api` without declaring it. Ten pyprojects put their
URLs in `[project]` instead of `[project.urls]`. Nothing pins Python below 3.14, where
`refitt-broker` cannot install. Fixing all of this turns three of the four CI jobs green and lets
every sync go `--frozen`.

*Horizon: now · Depends on: the refitt-host dependency decisions (git URL, lsdb bound) · Refs:
prerequisite for the test-suite entry (CI dies before pytest) and for any release*
**Seed:** [`issues/workspace-install-hygiene.md`](issues/workspace-install-hygiene.md)

## The test suite cannot collect, so CI is red for the wrong reasons

Sixteen test files still import the pre-split module tree (`refitt.core.web.*`, `refitt.web.api`,
`refitt.data.broker`). That hides 909 of the suite's roughly 1,280 tests behind collection errors.
Every symbol still exists under a new name, so the repair is a rename. A codemodded copy run against
ephemeral Postgres went 1216 passed, 0 failed once the session timezone, HOME isolation and rootkey
were handled. The cycle should also re-home each test with the distribution it exercises, tag the
53% of tests that carry no marker (so `-m unit` means something), and make the endpoint tests
hermetic. This is the factory's first real dogfood cycle.

*Horizon: now · Depends on: the install-hygiene entry for a green CI run, and a `/rf-harness` pass
hardening `temp_db.sh` / `temp_pg.sh` (see *A note on factory work*) · Refs: prerequisite for every
data-layer and API cycle*
**Seed:** [`issues/test-suite-repair.md`](issues/test-suite-repair.md)

## The documentation site cannot build, and has nothing in it

Invariant §K6 requires every CLI or public-API change to update the Sphinx docs in the same commit.
But `docs/website` is a 2019 quickstart stub with an empty toctree, and its `conf.py` names
`sphinx_rtd_theme` while only `furo` is installed. Every later cycle that touches docs would start
by fixing the build and inventing the site's structure on the spot. Scaffold it once: a working
build, the section skeleton (CLI, API, database, testing), and the docs check wired into CI.

*Horizon: near-term · Depends on: — · Refs: prerequisite in practice for every §K6-bound cycle*
**Seed:** [`issues/docs-site-scaffold.md`](issues/docs-site-scaffold.md)

## No modern release has ever been cut

The last PyPI release is `refitt` 0.24.0 from 2022. None of the ten split distributions exist on
PyPI, and the stored token predates them and is probably scoped too narrowly to create them. The
version drift spans 0.27.0 at the root, 0.26.1 in the members and `__version__`, 1.0.0 in
`refitt-host`, and 0.0.1 in the docs. The default branch is still `master`, 40 commits behind
`develop`. That keeps the new Dependabot config inactive and still runs the Poetry-era workflows
there. The first release under the new pipeline settles the version, the PyPI credentials and
projects, the `develop → master` promotion, and required status checks on `master`.

*Horizon: near-term · Depends on: the three entries above (a green CI on a frozen lock) · Refs: the
`/rf-release` skill is deliberately not ported yet; author it from this release's procedure (see
*A note on factory work*)*
**Seed:** [`issues/first-modern-release.md`](issues/first-modern-release.md)

---

# Part II — The model rewrite

Braden is restructuring the GTF light-curve model to avoid the failure modes of the 2026 season.
`refitt-host` (Part I) was its first piece. The second, a rewrite of `py/models/refitt-gtf`, is
expected as a PR. It is listed apart from Part I because it is gated on two things outside this
repository: the PR itself, and a record of what production actually ran.

## Integrate Braden's refitt-gtf rewrite without losing the production entry-point changes

During the 2026 season the GTF entry point gained data-path options and a no-coverage exit
contract. Git holds exactly one change on top of Braden's original commit (`879e7f8`): the
`--tns_path` / `--parsnip_path` / `--classifier_path` options, a REFITT-cache TNS read, and a
`NO_PANSTARRS_DATA` exit-0 path. The "few fixes deep in the implementation" exist nowhere in git or
on the maintainer's laptop. They most likely live uncommitted in the production working copy, its
wrapper script, or its environment. Capture that copy on a `wip/gtf-production-delta` branch
*before* the PR lands. Then compare three ways (base `4b675ee`, production, Braden's branch) and
carry the *behaviors* forward onto the new code, not the lines. Separately, gtf ships a regular
`refitt/__init__.py` that would shadow the whole workspace namespace if it were ever installed
alongside it.

*Horizon: when the PR opens · Depends on: Braden's PR; the production working-copy capture
(maintainer action); the PR-intake harness flow (see *A note on factory work*) · Refs: overlaps
`refitt-host` (`outside_catalog` is the structural successor of `NO_PANSTARRS_DATA`)*
**Seed:** [`issues/refitt-gtf-rewrite.md`](issues/refitt-gtf-rewrite.md)

---

# Part III — The data layer

The portal needs a schema that can change. Today it cannot: there is no migration path (§C2), the
column metadata exists twice (§C1), the seed's foreign keys are positional integers (§C3), and
SQLite and Postgres disagree on foreign keys, JSON and timestamps (§C4). Each of these is a Tier 2
"honor until redesigned" constraint. These cycles are that redesign, and `/rf-harness` retires each
constraint once its cycle lands. Production's live schema is unknown from this repository and must
be inspected before migrations are adopted.

## `refitt database init --core` leaves a production database unable to ingest

The core seed role has nine JSON files, but `ENTITIES['core']` loads only five. A database created
with `--core` therefore has no `source`, `source_type`, `observation_type` or `file_type` rows. Broker
ingest, forecast publishing and `POST /recommendation/<id>/observed` all look those rows up by name,
so each fails with NotFound on a freshly initialized production database. `--core` and `--test` are
also mutually exclusive, which the factory's own `ears.md` example gets wrong.

*Horizon: near-term · Depends on: — (small; verifiable on `temp_db.sh` once the harness pass lands)
· Refs: the seed-dataset entry reworks the same loader later*
**Seed:** [`issues/core-seed-incomplete.md`](issues/core-seed-incomplete.md)

## Every model declares its columns twice

All 25 models re-declare a `columns` dict, and 12 also declare a `relationships` dict, that duplicate
the SQLAlchemy mapping (§C1). Today the two agree exactly, in declaration order. They feed
`to_json`, `update()`'s route-unknown-fields-into-`data` behavior that the API relies on, and the
`refitt database query` CLI. Deriving them from the mapper is safe only if it keeps the 31
many-to-one relationships and drops the 28 backrefs. Including the backrefs would change every
`to_json(join=True)` payload. The same pass can retire the legacy `declarative_base` and the
module-level pandas import.

*Horizon: mid-term · Depends on: test-suite repair (model tests must run under `-m unit` first) ·
Refs: retires invariant §C1*
**Seed:** [`issues/model-derive-columns.md`](issues/model-derive-columns.md)

## The schema has no migration path

The schema lifecycle is `create_all()` / `drop_all()` and nothing else (§C2). There is no Alembic, so
every structural change the portal needs requires a migration that cannot be written today. That
includes multiple sessions per client, auth tables for human login, JSONB, and dropping the six
vestigial StreamKit tables. Adopting migrations means baselining a production schema this
repository has no record of. Schema names come from config at class-definition time (§4).
Migrations also need batch mode on SQLite, and test databases must be built the same way production
is.

*Horizon: mid-term · Depends on: test-suite repair; a look at the live production schema · Refs:
prerequisite for the dialect, seed-v2 and portal-auth entries; retires invariant §C2*
**Seed:** [`issues/db-migrations.md`](issues/db-migrations.md)

## SQLite and Postgres disagree, and the fast verify tier hides it

The `JSON` variant used on Postgres is plain `json`, not `jsonb`, despite its import alias. That
rules out GIN indexing and equality, so the `query` CLI's alias filter is likely broken on Postgres.
SQLite runs without `PRAGMA foreign_keys`, so cascades and constraint errors behave differently
across the two verify tiers. Timestamps come back timezone-aware from one dialect and naive from the
other, and `to_json` emits them with `str()`, so API timestamp strings depend on the backend. The
"Postgres-only `->>`" claim that shapes the two-tier verify substrate is stale for SQLite 3.38+.

*Horizon: mid-term · Depends on: the migrations entry (JSONB is a migration) · Refs: retires
invariant §C4; corrects factory prose via `/rf-harness`*
**Seed:** [`issues/db-dialect-parity.md`](issues/db-dialect-parity.md)

## The test seed cannot exercise the portal

All 323 test-seed rows carry `id: null`, so every foreign key in the seed is a hard-coded load-order
position. One authorization check depends on that order (`source type_id != 4`). The data is also
too thin to drive a portal. All 24 recommendations are already accepted, so `GET /recommendation`
returns nothing for every user. Every forecast model's data is empty. There is no level-1 admin
persona and no revoked client. The seven reference tables are byte-identical copies in `core/` and
`test/`. Seed v2 should be co-designed with the migrated schema and use explicit keys, a privilege
matrix of personas, recommendations in every state, models with real payloads, and dates relative to
now.

*Horizon: mid-term · Depends on: migrations, dialect parity · Refs: retires invariant §C3;
prerequisite for portal API tests*
**Seed:** [`issues/seed-dataset-v2.md`](issues/seed-dataset-v2.md)

---

# Part IV — The portal API

The API was built for machine clients holding a key:secret pair. A browser portal needs
human-friendly sessions, a stable serialized contract, CORS, pagination and a published schema, and
an app that can be built per test. Several of these changes amend Tier 1 invariants: the app shape
(§6), the auth posture and status mapping (§5), session scoping (§7), and import-time binding (§4).
Each such cycle therefore carries a constitution change through `/rf-harness` alongside its code,
and nearly every file it touches is on the high-blast-radius list.

## Small API defects that do not need the redesign

A malformed bearer token returns 500 instead of 403, because the token parser raises a `ValueError`
the status map does not cover. `PayloadTooLarge` (413) is raised for invalid *query parameters* at
five GET sites. Werkzeug errors outside `@endpoint`, other than 404/405, come back as HTML rather
than the envelope. These are independent of the redesign entries below and small enough to land
early.

*Horizon: near-term · Depends on: test-suite repair · Refs: —*
**Seed:** [`issues/api-quick-fixes.md`](issues/api-quick-fixes.md)

## The ORM row is the API contract

Routes return `Model.to_json()` directly, so column names, raw JSON blobs and dialect-dependent
`str(datetime)` strings go straight to clients. `refitt-client` and the tests consume exactly that.
Any rename or retype in the data layer is therefore a breaking API change. A serialization layer
between the ORM and the wire has to land before the data-model cycles start renaming things.

*Horizon: mid-term · Depends on: test-suite repair · Refs: prerequisite for any column rename in
Part III and for the portal contract entry*
**Seed:** [`issues/api-serialization-layer.md`](issues/api-serialization-layer.md)

## The server cannot be built per test, and sessions are not request-scoped

One global Flask `application` gets its routes through import side effects. The database binds at
import, so isolated per-test apps or databases are impossible, and the endpoint tests run end-to-end
over HTTP against a live server. Models fall back to process-global sessions 65 times and commit
inside 20 model methods, so a route cannot compose writes atomically. Four GET routes write, which
already breaks §7. An app factory with Blueprints and request-scoped sessions fixes testability and
atomicity together, and needs the §4/§6/§7 amendments.

*Horizon: mid-term · Depends on: test-suite repair · Refs: amends invariants §4, §6, §7; enables
hermetic endpoint tests*
**Seed:** [`issues/api-app-factory.md`](issues/api-app-factory.md)

## The API has no contract a browser client can be built against

Message text is the only error contract. The SDK detects expiry by matching `'Token expired'`, and
the tests assert 215 exact strings. There are no pagination, filtering or sorting conventions. There
is no OpenAPI schema (the bespoke `info` dicts are the only description), no version prefix, and no
CORS. A TypeScript client cannot be generated, and `refitt.org` cannot call the API cross-origin.

*Horizon: mid-term · Depends on: the serialization layer; the app factory · Refs: amends invariant
§6 (envelope)*
**Seed:** [`issues/api-contract-portal.md`](issues/api-contract-portal.md)

## Browser sessions need a real auth lifecycle

Credentials are one machine key:secret per user, and refreshing a token requires that long-lived
secret. A browser would have to hold it, or a backend-for-frontend with cookies would need CSRF
protection, which is absent. Bearer validation never consults the `Session` row. The schema allows
one session per client. There is no refresh, logout or server-side revocation, and the routes that
mint and rotate credentials are non-idempotent GETs. The portal needs human login, refresh rotation,
revocation and multiple sessions, which together redesign §5's posture under a human gate.

*Horizon: mid-term to long-term · Depends on: migrations; the app factory · Refs: amends invariants
§5, §7*
**Seed:** [`issues/portal-auth-sessions.md`](issues/portal-auth-sessions.md)

## Authorization is hand-written per route

Beyond the single `level` threshold, every ownership and visibility rule is written inline in its
route (`is_owner`, `is_viewable`, `is_associated`, `_get_source`, …). The admin bypass is applied
inconsistently, and one rule depends on seed load order. The portal will multiply these routes. A
central policy layer makes the rules reviewable in one place and testable as a matrix against the
seed-v2 personas.

*Horizon: long-term · Depends on: the app factory; seed v2 (personas) · Refs: —*
**Seed:** [`issues/authz-policy-layer.md`](issues/authz-policy-layer.md)

---

# Settled questions

Recorded so they are not re-raised by the next review. These carry `status: declined` or
`status: accepted-behaviour` and are **not** queue entries. Work that *shipped* leaves no entry
here: the code refutes a re-filing on its own, and `spec/{slug}/` holds the account.

None recorded yet.

# A note on factory work

Changes to `.agents/` are not cycles and are not indexed here. `/rf-harness` applies them under a
human gate and records each decision in
[`.agents/factory/harness-log.md`](.agents/factory/harness-log.md). Several entries above depend on
harness work that the ledger carries as *deferred*:

- **Harden `temp_db.sh` / `temp_pg.sh`** before the test-suite cycle. The SQLite tier cannot run
  unattended today: `init` always prompts on SQLite, a user config conflicts with the forced
  settings, and the documented relative test paths cannot resolve. The Postgres tier needs HOME and
  config isolation, `PGTZ`, free ports, real readiness probes, and a daemon check.
- **A PR-intake flow** (check out a contributor's PR, conform it, then merge) before Braden's
  refitt-gtf PR.
- **`/rf-release`**, authored from the first modern release's actual procedure.
- **Constitution corrections** the evidence sweep found. The workspace map omits `refitt-host`. The
  stated dependency order `core → assets → data → api` is inverted for data and api: `refitt-data`
  imports `refitt-api`. The SQLite `->>` limitation is stale.

# A note on security work

Security hardening is tracked separately and is **not** listed here. Fixes land as ordinary public
commits and PRs. But this repository is public, and a standing, ranked inventory of unremediated
weaknesses is not something to publish. See *Deferred work* in [`AGENTS.md`](AGENTS.md) §5 for how
the two lanes divide.
