---
status: unshaped
kind: refactor
appetite: big
lane: public
---

# Conform `refitt-host` to the workspace

## Problem

PR #24 (squash `8e85fc8`, Braden Garretson, 2026-09-26) added `py/libs/refitt-host`, a host-galaxy
association library. It ranks candidates from **local** PS1 and REGALADE HATS catalogs with a
clean-room port of astro-prost's probabilistic association. It was merged deliberately before
conformance. The PR touched only `py/libs/refitt-host/**` (19 files): no `uv.lock`, root
`pyproject.toml`, `AGENTS.md`, docs, or CI changes. Because the `py/libs/*` workspace glob
auto-enrolls it, it is already a member.

**Invariant conflicts:**

| Invariant | Status | Evidence |
|---|---|---|
| §1 namespace integrity (Tier 1) | violated | Ships a top-level `refitt_host` package (`pyproject.toml:24-25`, `packages = ["src/refitt_host"]`). It does not ship `refitt/__init__.py`, so the namespace is not collapsed, but it is the only member outside `refitt.*`. |
| §3 / §K1 version lockstep | violated, widens the drift | `version = "1.0.0"` (`pyproject.toml:7`), against 0.26.1 in members and 0.27.0 at the root. |
| §K2 test markers | violated | 0 of 15 tests tagged, so `pytest -m unit` deselects all of them. The member config has `testpaths` only and no `--strict-markers` (`pyproject.toml:30-31`). |
| §K5 Python 3.12–3.13 | violated | `requires-python = ">=3.11"` (`pyproject.toml:10`); `python=3.11` (`environment.yml:5`). |
| §K6 same-commit docs | violated | New public API and script, no Sphinx page. |
| §2 client boundary | not violated | Imports no `refitt.*`; nothing depends on it. It would be violated if a `refitt-client host …` command were ever added. |

**Workspace-wide effects (reproduced in scratch copies):**
- **Not in `uv.lock`.** The lock was already stale before #24 (140 packages); with refitt-host and
  all its extras a re-lock resolves 200.
- **Its optional `[hats]` extra changes everyone's pandas.** It requires `lsdb>=0.4` with no upper
  bound, which resolves to lsdb 0.11.0 (2026-09-21). That pulls nested-pandas 0.7 (`pandas>=3`) and
  hats 0.11 (`numpy>=2.3`). Because uv resolves every extra into one universal lock, `refitt-data`
  and `refitt-admin` move from pandas 2.2.3 → **3.0.6** and numpy 2.2.4 → **2.5.3**. Capping
  `lsdb>=0.10,<0.11` keeps pandas 2.x; numpy still moves to ≥2.3.
- **Its git-URL extra breaks publishing and the image build.** The `[nuclearity]` extra is
  `iinuclear @ git+https://github.com/gmzsebastian/iinuclear.git@f170ee4…` (`pyproject.toml:21`,
  with `allow-direct-references`).
  - PyPI rejects direct-URL `Requires-Dist`, so `uv publish` would fail on refitt-host, possibly
    mid-release.
  - Re-locking needs a `git` binary, and `python:3.13-slim` has none. A local `docker build` fails at
    `Dockerfile:33` with `Git executable not found`, and `Apptainer:57` uses the same recipe.
    `docker.yml`'s path filter (`:16-22`) misses `py/**/pyproject.toml`, which is why #24 never
    exercised the image.
  - The pinned commit `f170ee4` *is* the `iinuclear 0.1` release on PyPI (pure wheel, 2025-07-09),
    so the URL can become `iinuclear==0.1`.
- **Two tests depend on the working directory.** `tests/test_find_host_script.py:6` resolves
  `Path("scripts/find_host.py")` against the CWD. From the repo root, which is how CI runs pytest,
  2 of 15 fail; all 15 pass from the package directory.

**Behavior defects:**
- **Silent failure.** On the base install (no `[hats]`, which is what `uv sync --all-packages`
  gives), the missing-`lsdb` `CatalogQueryError` (`catalog.py:136-138,178-180`) is swallowed by
  `CatalogRegistry.query` (`catalog.py:55-59`). Every lookup returns
  `AssociationResult(outcome='no_candidates')` and `scripts/find_host.py` exits 0.
  `lsdb.read_hats` sits outside the `try` (`:144,186`), so a bad path *with* lsdb installed raises
  instead, which is inconsistent.
- **Catalog name misspelled in emitted data.** The catalog is **REGALADE** (Tranin et al. 2026,
  A&A 706, A284), but output IDs and labels say `REGLADE` (`catalog.py:97,127`, class
  `RegladeLocalProvider` at `:94`). The API and CLI spell it `regalade`. Fix this before any result
  is persisted.
- `scripts/find_host.py` is not an entry point. It is not in the wheel, reaches the package through a
  `sys.path` hack (`:17-19`), and dispatches on a raw `"--input" in argv` check (`:101`).
- Outputs default to CWD-relative paths (`nuclearity.py:10`, `find_host.py:64`).
- A process-global stdout/stderr redirect (`catalog.py:75-80`) is not thread-safe under "one instance
  per worker".
- `scipy` is needed for one constant only (`gammaln(0.75)`, `astro_prost_math.py:16,67`).
- The scripts that build the multi-GB catalogs are referenced in `.gitignore:19-28` but not
  committed, so the required data cannot be reproduced from this repository.

## Why it was deferred

The maintainer chose to merge #24 as-is (2026-09-26) rather than ask the contributor to rework it,
and to conform it here instead. Every issue above is **pre-existing** on `develop`.

## Outcome / vision

`refitt-host` is an ordinary workspace distribution:
- a `refitt.<name>` portion with no top-level `__init__.py`
- the lockstep version, Python 3.12–3.13, house metadata (`[project.urls]`, not the invalid sibling
  keys)
- PyPI-installable dependencies, with heavy extras that do not silently re-major the rest of the
  workspace
- tagged tests that pass from the repo root
- loud failure when a configured catalog is unusable
- a docs page

## Sketch of the acceptance criteria

- **R1** — WHEN the workspace wheel set is built, the refitt-host wheel SHALL contain only
  `refitt/<name>/**`, and `import refitt.core, refitt.<name>` SHALL both succeed in one environment.
- **R2** — The refitt-host distribution SHALL declare the lockstep project version and
  `requires-python` within 3.12–3.13.
- **R3** — WHEN `uv build --all-packages --no-sources` runs, no refitt-host `Requires-Dist` SHALL be a
  direct URL.
- **R4** — WHEN the workspace is locked, `refitt-data` SHALL resolve the same pandas major version
  as before refitt-host joined, unless a pandas-3 move is an explicit, tested decision.
- **R5** — WHEN a configured catalog's backend is unavailable or its path is invalid, the
  association SHALL report an error for that catalog rather than `outcome='no_candidates'`, and the
  CLI SHALL exit non-zero (`cmdkit.app.exit_status`).
- **R6** — Emitted catalog identifiers SHALL use the catalog's correct name (REGALADE).
- **R7** — WHEN `uv run pytest -m unit` runs from the repo root, all refitt-host tests SHALL be
  selected and pass.
- **R8** — The docs site SHALL describe the API, any CLI, the data requirements and the extras.

## Notes

- Open questions for shaping:
  - **Q1.** Library only, or does it read catalog paths from REFITT config and log through
    `refitt.core`? The second places it at `core → host` and inherits §4 import-time fail-fast.
  - **Q2.** CLI home: a `refitt-host` console script, a `refitt host …` subcommand, or none for now?
  - **Q3.** Name: `refitt.host` collides in meaning with `refitt.database.model.Host`
    (`model.py:1574`, a *compute* host). Alternatives are `refitt.hostgal`, `refitt.galaxy`, …
  - **Q4.** Add it to the root meta-package's dependencies, or keep it opt-in?
  - **Q5.** License: relicense to Apache-2.0 (needs the contributor's agreement) with an astro-prost
    MIT notice, or keep a per-distribution MIT?
  - **Q6.** Heavy extras: cap `lsdb<0.11`, adopt pandas 3 workspace-wide on purpose, or keep the
    extras out of the universal lock? Should production images install `[hats]`? Without it the code
    cannot query catalogs.
  - **Q7.** Keep `environment.yml` for collaborator conda/HPC use, move it outside the workspace, or
    drop it?
  - **Q8.** Keep the `[nuclearity]` extra? It makes network calls to ALeRCE, TNS, MAST, SDSS and
    IRSA and reads TNS credentials from the environment.
  - **Q9.** Its relationship to gtf's DELIGHT-based `host_galaxy_association.py`: replace it,
    coexist, or retire it?
  - **Q10.** Where do the PS1/REGALADE HATS collections live in production, and do the build scripts
    belong in this repo?
- **Sequencing.** The rename changes import paths Braden's upcoming refitt-gtf PR may already use.
  Agree the new name with him before landing it, or land it after his PR.
- AGENTS.md's workspace map and DAG text need a `/rf-harness` update in step with this cycle (the
  libs table, "nine distributions", the dependency order).
- Related: [`workspace-install-hygiene.md`](workspace-install-hygiene.md) (lock regeneration),
  [`refitt-gtf-rewrite.md`](refitt-gtf-rewrite.md), [`docs-site-scaffold.md`](docs-site-scaffold.md).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
