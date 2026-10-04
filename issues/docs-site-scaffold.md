---
status: unshaped
kind: docs
appetite: small
lane: public
---

# Scaffold a documentation site that builds

## Problem

Invariant §K6 requires a CLI or public-API behavior change to update the Sphinx docs
(`docs/website`) in the same commit. `rf-review` runs a Sphinx build whenever `docs/website` is
touched. But the site does not build and has nothing in it:

- **`docs/website/source/`** holds only `index.rst`, with an empty toctree (`index.rst:9-12`), and a
  2019 quickstart `conf.py` with `release = '0.0.1'` (`conf.py:27,29`).
- **`conf.py` sets `html_theme = 'sphinx_rtd_theme'`**, but the docs dependency group and `uv.lock`
  contain only `furo`. A `sphinx-build` should therefore fail [static: not executed in the sweep].
- **There are no pages for the CLI, the REST API, the database, or testing.** The REST API's only
  description is the bespoke `info` dicts served at `/info`.
- **Help text has drifted from the code:**
  - `refitt auth`'s HELP advertises `-e`/`-l` short flags that do not exist (only
    `--expires`/`--level` are defined, `admin/auth.py:94,97`) and omits `--json` (line 100).
  - `refitt database init` does not document its `-s/--scope` option (`init.py:63` vs the USAGE/HELP
    at `init.py:28-44`).
- `.readthedocs.yaml` exists (from `8422947`) but has nothing real to publish.

## Why it was deferred

The docs site predates the workspace split and was never rebuilt. Every item is **pre-existing**.
Every Part III/IV cycle is §K6-bound, so leaving the site unscaffolded means each of those cycles
would invent the structure ad hoc.

## Outcome / vision

`sphinx-build -W` on `docs/website` succeeds locally and in CI. The site has a stable skeleton
(Overview, Install, CLI reference, REST API, Database, Testing/seed data, Contributing / the
factory) that later cycles fill in. The version comes from the single project version, not a
literal. Each CLI's `--help` output matches what it accepts.

## Sketch of the acceptance criteria

- **R1** — WHEN `uv run sphinx-build -W docs/website/source <out>` runs, it SHALL exit 0.
- **R2** — WHEN CI runs on a PR that touches `docs/website`, the docs build SHALL run and gate the PR.
- **R3** — The site's toctree SHALL contain the skeleton sections named above.
- **R4** — The rendered docs SHALL show the project version from the single version source.
- **R5** — WHEN `refitt auth --help` or `refitt database init --help` is printed, every option shown
  SHALL be accepted, and every accepted option SHALL be shown.

## Notes

- Small and independent, so it can run in parallel with the Part I repairs.
- The `docs/manpages` stub is in scope only if the shaping conversation decides REFITT ships man
  pages.
- Related: [`refitt-host-conform.md`](refitt-host-conform.md) (needs a page),
  [`api-contract-portal.md`](api-contract-portal.md) (OpenAPI rendering).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
