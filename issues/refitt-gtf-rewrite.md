---
status: unshaped
kind: feature
appetite: big
lane: public
---

# Integrate Braden's refitt-gtf rewrite without losing the production entry-point changes

## Problem

`py/models/refitt-gtf` is the GTF light-curve model: ANTARES light curves, PS1/Delight host
association, NED/SDSS/PS1 cross-match, a TNS cross-match, and ParSNIP fit and classification.
Braden Garretson added it in `4b675ee` (2025-01-23). It sits outside the uv workspace and runs as
scripts from a Windows-exported Python 3.10 conda environment (`refitt_environment.yml`). Braden is
preparing a structural rewrite meant to avoid the failure modes of the 2026 season. When it lands,
whatever the maintainer changed for production has to be carried forward onto the new code.

**What git holds: one change on top of `4b675ee`.** That is `879e7f8` (2026-07-23, pre-rebase
`f6d0c71`, identical content). It touches `analyze_lc.py` (+41/−10) and `refitt/query/tns.py`.

| # | where (HEAD `analyze_lc.py`) | change | class |
|---|---|---|---|
| H2 | `:43-47` | constants `TNS_PATH`, `PARSNIP_PATH`, `CLASSIFIER_PATH` under `~/refitt/lib/{tns,gtf}` | data paths |
| H3/H10 | `:48-51`, `:127-136` | `main()` takes and is passed the three paths | entry point |
| H9 | `:108-110` | new options `--tns_path`, `--parsnip_path`, `--classifier_path` (no help text) | entry point |
| H6 | `:78` | ParSNIP model and classifier load from those paths (were `./bts_ps1_bg.pt`, `./classifier`) | data paths |
| H5 | `:69` | TNS read switched from the raw `tns_data.zip` (`skiprows=1`) to REFITT's cached CSV (header on row 1) | TNS behavior |
| H8 | `:106` | `--plot_output_dir` default `./plot/` → `./` (nothing creates the folder; `plot.py:207` concatenates strings) | entry point |
| H4 | `:55-62` | `OSError('Empty or corrupt FITS file')` from host association → prints `NO_PANSTARRS_DATA: …` to **stderr** and **`sys.exit(0)`** | robustness |
| H11 | `tns.py:63-78` | **whitespace only**, despite the commit title | — |

- **H4 is an interface contract.** It exits 0 and writes no outputs. A caller can tell "no
  coverage" from success only by grepping stderr, so a production wrapper must parse it. That
  wrapper is not in the repository.
- **H4 also aborts the whole batch** in multi-ID mode, and its message prints the whole ID list.
- **The default paths encode the production account's layout** (`~/refitt/lib`). That matches
  neither REFITT's platform site (`~/.refitt/lib`, `platform.py:30`) nor the maintainer's laptop.
- **Still unparameterized:**
  - `--host_image_directory` defaults to the CWD-relative `../../host` and requires a pre-existing
    `<dir>/fits/` (`host_galaxy_association.py:36`).
  - The CSV outputs default to the CWD.

**What git does not hold.** The maintainer recalls "a few fixes deep in the implementation to handle
a lot of exceptions". No implementation module changed in git. A sweep of this machine found no
other copy of the gtf code. It checked every ref, the reflogs, the stash, unreachable
commits/trees/blobs, three snapshot archives, a targeted `$HOME` search, and the logs of a
production-site mirror (`~/Data/Refitt`). The deep fixes most likely live **uncommitted in the
production working copy** (RCAC), its wrapper script, or patches inside its environment's
`site-packages`. Unhandled failure sites at HEAD, checked first when diffing production:
- `cross_match_galaxy.py:24`: NED `NoSourcesError` is uncaught, while SDSS and PS1 are caught at
  `:27-44`.
- `sdss.py:63`: `query_sql` may return `None`, then `.to_pandas()` raises.
- `panstarrs.py:279`: `fitsurl[0]` IndexError, or `fits.open` OSError.
- `antares.py:105-111`: unknown IDs return `None`; no timeouts on any `requests` call.
- `host_galaxy_association.py:36,56-59,119-138`: missing or empty `fits/`; Delight failures.
- `plot.py:204,209`: `model_dof == 0`; redshift indexing.

**Namespace hazard.** gtf ships `refitt/__init__.py`, a *regular* package named `refitt`. A regular
package beats PEP-420 portions regardless of `sys.path` order (verified). So if gtf were installed
alongside the workspace, `import refitt.core` would fail. Every `refitt.*` import would first run
gtf's eager `__init__`, which pulls in tensorflow, torch and antares. That would also break the
client boundary (§2). The hazard is latent only while gtf keeps its own Python 3.10 environment.

## Why it was deferred

It is gated on things outside this repository: Braden's PR, and a record of what production ran.
The maintainer also wants contributor PRs checked out and conformed *before* merging, which needs a
PR-intake harness flow; that is deferred in `.agents/factory/harness-log.md`.

## Outcome / vision

Braden's rewrite lands on `develop` with every production behavior the maintainer relies on
re-instrumented. Those are expressed as requirements, not replayed lines. gtf no longer shadows the
`refitt` namespace. Its paths, credentials and failure reporting follow REFITT conventions.

## Sketch of the acceptance criteria

Behaviors known from git; extend with whatever the production capture recovers:
- **R1** — The TNS catalog path SHALL be configurable and SHALL read REFITT's cached CSV format,
  preferring `refitt-tns`'s configured cache over a hard-coded path.
- **R2** — The ParSNIP model and classifier paths SHALL be configurable.
- **R3** — WHEN a plot output directory does not exist, the entry point SHALL create it.
- **R4** — WHEN a target has no PS1 coverage, the entry point SHALL report it per target, without
  aborting the rest of the batch, in a form the production wrapper can consume (renegotiate the
  `NO_PANSTARRS_DATA` + exit-0 contract, or adopt refitt-host's `outside_catalog`).
- **R5** — The host-image directory SHALL be configurable without CWD-relative defaults.
- **R6** — WHEN gtf's code is importable in the same environment as the workspace,
  `import refitt.core` SHALL still succeed.
- **R7** — Credentials (e.g. TNS bot credentials) SHALL come from REFITT configuration, never from
  source.

## Notes

- **Before the PR lands: capture production (maintainer action).**
  1. On the production host, commit the gtf working copy as-is to `wip/gtf-production-delta`, after
     checking for secrets, `*.pt`, FITS, CSV and PNG outputs. If the copy is a plain directory,
     `rsync` it onto a branch off `develop` instead.
  2. In the same branch (e.g. under `py/models/refitt-gtf/ops/`), add:
     - the wrapper / cron / Slurm script that invokes `analyze_lc.py`
     - an export of the production environment
     - checksums of the model artifacts
     - whether `~/refitt` is a symlink to `~/.refitt`
  3. Diff the production environment's `delight`, `parsnip`, `lcdata`, `antares_client` and
     `astroquery` against pristine wheels, in case fixes were patched there.
- **When the PR opens:**
  1. `git fetch origin pull/<N>/head:pr-gtf-rewrite`.
  2. `git diff 4b675ee wip/gtf-production-delta` (ours).
  3. `git diff develop wip/gtf-production-delta` (the residue not yet in git).
  4. `git diff 4b675ee pr-gtf-rewrite` (theirs).
  5. Optionally `git merge-tree --write-tree --merge-base=4b675ee …`.
  6. Turn each hunk of "ours" into a behavioral requirement and verify it against Braden's code.
- **Coordinate with refitt-host.** The rewrite likely builds on `refitt-host`, whose conformance
  renames its package. Sequence or agree the name with Braden; see
  [`refitt-host-conform.md`](refitt-host-conform.md) (Q9 covers the host-association overlap).
- Whether gtf joins the workspace (it has no `pyproject.toml` today, and its Python 3.10 / TF 2.12 /
  torch 1.12 stack conflicts with 3.12–3.13) is a shaping decision. `train_parsnip_model.py`
  hard-codes CUDA; `score_lc.py` is unused.
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04 (full hunk-level inventory available on
  request; regenerate with `git diff 4b675ee 879e7f8 -- py/models/refitt-gtf`).
