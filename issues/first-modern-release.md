---
status: unshaped
kind: release
appetite: small
lane: public
---

# Cut the first release under the modern pipeline

## Problem

REFITT has not published a release in four years, and the new pipeline (`8422947`) has never fired.

- **PyPI.** `refitt` exists, but its latest release is 0.24.0 (2022-06-11). The other ten names all
  return 404: refitt-core, -data, -api, -assets, -admin, -server, -client, -broker, -tns and -host.
  - The repo secret `PYPI_TOKEN` was created 2021-04-16, before the split. A token scoped to the
    `refitt` project cannot create new projects, so the first upload needs an account-scoped token
    or Trusted Publishing "pending publishers". The CI GOAL deferred OIDC.
  - `publish.yml` now builds 11 distributions, but its comments say "9 members" and "10 uploads"
    (`:34`, `:58`).
- **Version drift (§3 / §K1):**

  | location | version |
  |---|---|
  | root `pyproject.toml:3` | 0.27.0 |
  | the nine members' `pyproject.toml:3`, `refitt.core.__version__` (`core/__init__.py:28`), `uv.lock:1211` | 0.26.1 |
  | `refitt-host` | 1.0.0 |
  | `docs/website/source/conf.py` | 0.0.1 |

  - `refitt.core.__authors__` (`__init__.py:29-37`) omits two authors listed in the root pyproject.
  - Sibling dependencies in the built wheels are unpinned (`Requires-Dist: refitt-core`), so nothing
    guarantees a lockstep install.
- **Branches.**
  - The default branch is `master`, 40 commits behind `develop` and 20 ahead. All 20 are git-flow
    release merges, and they differ in content from the merge base by one version line.
  - A `develop → master` merge conflicts on exactly one hunk, the root version.
  - Until `master` has `develop`'s `.github/`:
    - Dependabot reads its config only from the default branch, so the uv/actions config is
      **inactive**.
    - `workflow_dispatch` is unavailable for `publish.yml`/`docker.yml`.
    - The Poetry-era workflows on `master` remain the registered ones.
  - `master` is protected but requires **no status checks and no reviews**.
- **Releases and tags.**
  - GitHub's latest release is 0.24.0. 0.25.0, 0.26.0 and 0.26.1 have tags but no releases.
  - `git describe --tags` on `develop` gives `0.17.0-289-g…`, because tags since 0.18.0 sit on
    `master` merge commits. The Apptainer `VERSION` from `make apptainer` (Makefile:40) is therefore
    wrong.
- **Hygiene.**
  - Stale branches remain: `origin/fix/json_file_output` (PR #23 merged), `origin/qNRfyXqfcpBxIhuk`
    (identical to `master`, no PR), and local remote-tracking refs for the closed Dependabot PRs.
  - The maintainer's local clone is missing one tree object (`d75b7e8e`, the 2020 `refitt/apps`
    tree). GitHub still has it. `git fetch --refetch` or a fresh clone repairs it.

## Why it was deferred

Release prep needs a green CI on a frozen lock first. The CI GOAL left versioning, the lock
regeneration and PyPI credentials as explicit follow-ups. All of the above is **pre-existing**.

## Outcome / vision

One version across every distribution, `__version__`, and the docs. All eleven names exist on PyPI
and publish together on a GitHub Release. `develop` promoted to `master`, so Dependabot and the
modern workflows are live on the default branch. `master` requires the CI checks. The procedure is
written down as `/rf-release`.

## Sketch of the acceptance criteria

- **R1** — Every distribution, `refitt.core.__version__`, and the docs SHALL carry one version, and
  the factory's version check SHALL pass.
- **R2** — WHEN a GitHub Release is published, `publish.yml` SHALL upload every workspace
  distribution, and each SHALL be installable from PyPI at that version.
- **R3** — WHEN the release lands, `docker.yml` SHALL push `ghcr.io/refitt/refitt` at that version,
  and the image's `refitt --version` SHALL print it.
- **R4** — After promotion, the default branch SHALL carry the modern `.github/` (Dependabot,
  workflows), and `master` SHALL require the CI status checks.

## Notes

- Decide in shaping: the version number (0.27.0 or a reset), whether siblings pin `==` each other,
  PyPI auth (account token vs Trusted Publishing), and whether to promote `develop → master` early
  (to activate Dependabot security updates) ahead of the release itself.
- The `/rf-release` harness skill is deliberately not ported from HyperShell yet. Author it from this
  release's actual procedure; it is a deferred item in `.agents/factory/harness-log.md`.
- Related: [`workspace-install-hygiene.md`](workspace-install-hygiene.md),
  [`test-suite-repair.md`](test-suite-repair.md), [`refitt-host-conform.md`](refitt-host-conform.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
