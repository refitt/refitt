---
status: unshaped
kind: fix
appetite: small
lane: public
---

# A stale lock and undeclared dependencies break the install before any test runs

## Problem

All four jobs of CI run 36265361934 (`develop` @ `8e85fc8`) fail. Three of the failures happen
before a single test executes:

1. **`tests (3.12)` / `tests (3.13)`** die at "Initialize + seed the test database"
   (`uv run refitt database init --test`):
   ```
   File ".../refitt/forecast/model.py", line 18: from astropy.time import Time
   AttributeError: module 'numpy' has no attribute 'in1d'. Did you mean: 'int16'?
   ```
   - `uv.lock` has `revision = 1`, and its `[manifest] members` (`uv.lock:10-21`) omit
     `refitt-host`, so `uv lock --check` fails.
   - The non-frozen `uv sync --all-packages` (`tests.yml:84`) therefore re-resolves: 140 → 200
     packages, numpy 2.2.4 → 2.5.3, pandas 2.2.3 → 3.0.6. That leaves **astropy at 7.0.1**, which
     is incompatible with numpy 2.5.
   - No pyproject declares astropy. It reaches the lock only through `antares-client` and
     `astropy-healpix`, but `refitt-admin` imports it (`refitt/forecast/model.py:18`,
     `admin/observation/publish.py:21-22`), and so does `refitt-broker` (`broker/antares.py:17`).
   - Installing `astropy>=7.2` in the re-locked env makes `refitt --version` work again.
2. **Client install boundary** fails: `refitt-client boundary violated (invariant §2): pulled in
   sqlalchemy`.
   - `py/libs/refitt-api/pyproject.toml:32` declares `sqlalchemy>=2.0.32` for a single import at
     `refitt/api/response.py:12`: `from sqlalchemy.exc import NoResultFound as RecordNotFound`.
   - `refitt.client` imports `refitt.api.response` (`refitt/client/__init__.py:33`).
3. **Package metadata** fails ten times with ``[ERROR] `project` must not contain {'repository',
   'homepage', 'documentation'} properties``.
   - Every refitt pyproject (the root plus 9 members) has those keys at lines 6-8, a Poetry-ism.
   - hatchling silently drops them, so today's wheels carry **no Project-URL**.
   - With the keys moved to `[project.urls]`, `twine check --strict` passes on all 22 artifacts.

Other under- and over-declarations, from a static scan of imports against declared deps:
- `refitt-api` imports `refitt-core`, `cryptography` and `cmdkit` (`token.py:21-25`) but declares
  only `sqlalchemy` and `requests`.
- `refitt-data` imports `refitt-api` (`database/model.py:40`: `from refitt.api.token import Key,
  Secret, Token, JWT`) without declaring it.
  - The real layering is therefore `core ← {assets, api} ← data`, which contradicts AGENTS.md's
    `core → assets → data → api`. If api depended on data, the client boundary could not hold.

Environment pins:
- With no `.python-version` and no upper bound on `requires-python`, a local `uv sync` picks Python
  3.14.
- There, `refitt-broker` cannot install: antares-client 1.8.0 → `bson==0.5.10` fails to build
  (`pkgutil.find_loader` removed).
- Python 3.13 works.
- Nothing syncs `--frozen`: `tests.yml:84`, `Dockerfile:33`, `Apptainer:57`, `Makefile:14`,
  `.readthedocs.yaml`.
- `docker.yml` has never run on GitHub. Its PR path filter misses member pyprojects, and it has no
  image smoke test (`docker run … refitt --version`). `Dockerfile:12` and `Apptainer:10` use an
  unpinned `ghcr.io/astral-sh/uv:latest`.

## Why it was deferred

These problems predate the factory. The CI/DevOps modernization (`8422947`) deliberately left the
lock non-frozen until a librdkafka-capable environment could regenerate it. Its GOAL records "switch
to `--frozen` after". Every item is **pre-existing** on `develop`, and #24 widened the lock gap.

## Outcome / vision

Every distribution declares what it imports. The lock is current and is the only source of truth
(`--frozen` everywhere). `refitt-client` installs without SQLAlchemy. Metadata validates and the
built wheels carry their URLs. The Python version is pinned to the supported range. The image build
is exercised on every PR that can break it.

## Sketch of the acceptance criteria

- **R1** — WHEN `uv lock --check` runs on `develop`, it SHALL succeed.
- **R2** — WHEN CI, the Dockerfile, the Apptainer recipe or the Makefile syncs the environment, it
  SHALL do so `--frozen`.
- **R3** — WHEN a fresh environment is synced from the lock, `uv run refitt --version` SHALL print
  the project version and exit 0.
- **R4** — WHEN the client-boundary job installs `refitt-client` from built wheels, the installed set
  SHALL contain none of numpy, scipy, pandas, sqlalchemy or astropy.
- **R5** — WHEN the metadata job validates every pyproject, it SHALL pass, and each built wheel SHALL
  carry its Project-URL entries.
- **R6** — Every distribution SHALL declare each third-party and sibling package it imports.
- **R7** — WHEN a PR changes any workspace pyproject or `uv.lock`, the image build SHALL run, and it
  SHALL run the built image's `refitt --version` as a smoke test.

## Notes

- Ordering: settle refitt-host's dependency choices first (the git-URL extra and the `lsdb` bound),
  or the regenerated lock inherits a git source and pandas 3. See
  [`refitt-host-conform.md`](refitt-host-conform.md).
- Regenerate the lock on Python 3.13 with the `.env` build paths sourced (librdkafka, libpq
  `pg_config`). Each re-lock rewrites roughly +2.7k/−0.7k lines.
- Until this lands, a plain local `uv run` re-locks and dirties `uv.lock`. Use `UV_NO_SYNC=1`.
- AGENTS.md's stated dependency order needs a `/rf-harness` correction to match the real edges.
- Related: [`test-suite-repair.md`](test-suite-repair.md),
  [`first-modern-release.md`](first-modern-release.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
