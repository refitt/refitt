# GOAL — Modernize REFITT CI/DevOps

- **slug:** ci-devops-modernization
- **kind:** feature
- **appetite:** big

## Problem

REFITT's CI/CD is ~3 years stale and structurally broken. Both GitHub Actions workflows drive
**Poetry** against a repo that has fully migrated to a **uv workspace + hatchling**; `publish.yml`
installs Poetry via the **removed `get-poetry.py`** endpoint (dead today) and can publish only **one**
package though REFITT ships **10 distributions** (9 members + the `refitt` metapackage); `tests.yml`
pins **Python 3.10** (project requires ≥3.12) and runs a TestPyPI publish *inside the test job*; and
the root `Dockerfile` is **conda/Miniconda, single-stage, Python 3.10, no non-root user**. There is
no Apptainer, `.dockerignore`, `.readthedocs.yaml`, `dependabot`, least-privilege `permissions`,
`concurrency` control, or version matrix. REFITT cannot currently produce a correct release or a
modern deployable artifact — and it deploys on **HPC clusters** where Apptainer, not Docker, is the
norm.

## Outcome / vision

A uv-native CI/DevOps foundation mirroring HyperShell's proven practices, adapted to REFITT's
monorepo and HPC reality: tests run on a supported Python matrix against a pinned Postgres; a GitHub
Release builds and publishes **all 10 distributions** to PyPI; a modern **fat GHCR container** ships
with a synced **Apptainer** image for HPC; docs build on ReadTheDocs via uv; Dependabot keeps actions
current; every workflow is least-privilege with concurrency control. Two guard jobs prevent whole
classes of release failure, including one that enforces the **`refitt-client` no-data-science-deps
boundary** (invariant §2) in CI.

## Acceptance criteria (the contract)

- **R1** — When code is pushed to `master`/`develop` or a PR targets `develop`, the tests workflow
  SHALL run `pytest` via `uv` across a Python matrix (3.12, 3.13) with `fail-fast: false`, under
  top-level `permissions: contents: read` and a `concurrency` group keyed on `github.ref` with
  `cancel-in-progress: true`.
- **R2** — While running tests, the workflow SHALL provision a **pinned** `postgres:16` service,
  install the native build libs (`libpq-dev`, `librdkafka-dev`), `uv sync`, run
  `uv run refitt database init --test`, start `refitt-server`, and drive `pytest` — using the
  `REFITT_DATABASE_DEFAULT_*` / `REFITT_API_*` env contract.
- **R3** — The CI SHALL include a **client-boundary guard** job that builds the `refitt-client` wheel,
  installs it `--only-binary=:all:` from local wheels, and FAILS if `refitt-data`, `numpy`, `pandas`,
  `scipy`, `sqlalchemy`, or `astropy` are pulled in (enforces invariant §2).
- **R4** — The CI SHALL include a **metadata guard** job that builds sdist+wheel for all packages and
  runs `validate-pyproject` + `twine check --strict` (prevents the "README failed to render" outage
  class).
- **R5** — When a GitHub Release is published (or the workflow is dispatched), the publish workflow
  SHALL build **all 10 distributions** via `uv build --all-packages --no-sources` and upload them to
  PyPI via `uv publish --check-url` using an **API token** (`UV_PUBLISH_TOKEN`), with top-level
  `permissions: contents: read`, `concurrency` with `cancel-in-progress: false`, and artifacts
  retained (`if-no-files-found: error`).
- **R6** — When a Release is published (or dispatched), a docker workflow SHALL build a **fat
  linux/amd64** image on `ubuntu-latest` and push it to **ghcr.io** with `pep440` + `sha` tags via
  `docker/metadata-action`; on a `Dockerfile`/workflow PR it SHALL build **without pushing** as a
  guardrail.
- **R7** — The `Dockerfile` SHALL be a uv **multi-stage** build from a slim Python base, install the
  native runtime libs (`libpq5`, `librdkafka1`), run as a **non-root** user, and provide all five
  console entry points.
- **R8** — An `Apptainer` definition SHALL build the equivalent image from the **same uv recipe** for
  HPC, kept in sync with the `Dockerfile`, with the version passed as a build argument.
- **R9** — A `.readthedocs.yaml` SHALL build the docs via uv (`uv sync ... --group docs`) on a pinned
  OS/Python, using `docs/website/source/conf.py`.
- **R10** — A `.github/dependabot.yml` SHALL track `github-actions` (weekly, grouped) and `uv`
  **security-updates only** (floors held for RHEL/EPEL parity).
- **R11** — All third-party actions in the publish and docker workflows SHALL be **SHA-pinned** with
  `# vX.Y.Z` comments.
- **R12** — A `.dockerignore` SHALL trim the `COPY` build context (exclude `.venv`, `.git`, `.env`,
  `.security`, caches, `dist`, `docs`, `tests`).

## Non-goals (no-gos)

- **Version single-source reconciliation** (root `0.27.0` vs members `0.26.1`) and the coupled
  `uv.lock` regeneration — deferred to a **release-prep** follow-up (it requires a working
  librdkafka-enabled env; the CI mechanism works with the current unpinned sibling deps).
- **Repairing the application test suite / broken pre-split imports** — a sibling feature ("Repair
  REFITT test suite"); the tests job runs honestly and may be RED until then (no `continue-on-error`
  faking).
- **PyPI Trusted Publishing (OIDC)** — chose API token for now (fewer moving parts; no 9× per-project
  registration). Revisit as a hardening step.
- **cosign signing + SLSA provenance attestation**, **multi-arch arm64 image**, **per-app images**,
  and **migrating off hatchling** — hardening/scale follow-ups (amd64-first; structure left ready).

## Clarifications

- **Q:** Publish scope + mechanism? — **A:** All 10 lockstep on a GitHub Release, **PyPI API token**
  (`UV_PUBLISH_TOKEN`) (resolved 2026-07-23).
- **Q:** Containers? — **A:** **Fat GHCR image + Apptainer** for HPC; amd64-first (resolved
  2026-07-23).
- **Q:** Scope boundary? — **A:** **CI-config only**; test-suite repair is a sibling feature
  (resolved 2026-07-23).
- **Q:** Native-dep fragility (librdkafka)? — **A:** **Install system libs** in CI/Docker **+ add the
  wheels-only guard** job; keep the dependency graph as-is (resolved 2026-07-23).

## Related materials

- HyperShell reference: `.github/workflows/{tests,publish,docker}.yml`, `Dockerfile`, `Apptainer`,
  `.dockerignore`, `.readthedocs.yaml`, `.github/dependabot.yml` in
  `github.com/hypershell/hypershell`.
- Blocker surfaced during this work: `uv sync` fails building `confluent-kafka`
  (`antares-client` ← `refitt-broker`) without system `librdkafka` — the motivation for R2/R7 and the
  release-prep lock follow-up.
