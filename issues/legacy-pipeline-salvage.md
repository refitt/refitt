---
status: unshaped
kind: fix
appetite: small
lane: public
---

# Keep the legacy forecast pipeline producing targets until GTF replaces it

> **Candidate, not a contract.** This file records deferred work in enough detail that a future
> session does not have to re-derive it. It is **not** graded by `code-review` and must never be
> copied into `spec/{slug}/GOAL.md` verbatim: `code refitt feature` promotes it, and that is where
> appetite, non-goals and the R-IDs get negotiated with a human. The `status:` field above is the
> guard.

## Problem

The legacy pipeline is the daily batch job behind today's target list. It queries ANTARES for ZTF
loci, forecasts each light curve with the
[`refitt-forecast`](https://github.com/refitt/refitt-forecast) kernel, and ranks the forecasts into
`priority/priority.csv`. That file has been empty since 2026-11-09. Two independent defects cause
this, and a third skews the forecasts that survive. The evidence below comes from the job's own
outputs, read back from 2025-03 to 2026-11-12. None of the analysis needed a rerun.

1. **No new sources since 2026-10-29.** `get_objects_antares.py` fetches only loci carrying the
   ANTARES tag `refitt_newsources_snrcut`. ANTARES returned HTTP 500 on every attempt from
   2026-10-27 to 2026-11-01. Since then, no locus whose first alert falls after MJD 61342 carries
   the tag, though ANTARES keeps ingesting new loci every day and keeps updating the old ones. The
   pipeline therefore re-forecasts an aging, shrinking sample:
   - inputs per run fell from about 300 to 157;
   - sources younger than 15 days fell from about 130 to 20;
   - the newest first detection in every run since 2026-10-28 is the same source.

   `prioritize_old.py` keeps only forecasts within 7 days of peak (`|tpeak| ≤ 7`, with `moe < 0.5`
   and uncertainty ≤ 14). Past-peak sources fail that cut, so the list emptied:
   - 18–23 forecasts passed in September and October;
   - 1 forecast passed on 2026-11-12.

   This one is outside the code. The filter needs checking in ANTARES, by whoever holds the
   project's login there or by the ANTARES team.

2. **ZTF `i`-band points crash the forecast.**
   - `defs.antares_band_name_dict` is `{'g': 1, 'R': 2}`. ANTARES labels ZTF `i`-band points
     `"i"`, and `get_objects_antares.py` passes that label through to the target JSON as a string.
   - `kernel.GP_Boone` calls `int(pb)` on every passband, so `int('i')` raises `ValueError`.
   - `Transient.__init__` catches that `ValueError` and prints "Gaussian Process fit failed. I
     cannot proceed." Its comment says the handler is meant for light curves with a single point.
   - Every run since 2026-09-09 shows the same split: every target with an `i` point fails, and
     every target without one forecasts. There were 2 exceptions in about 14,000 targets.
   - The published history dates the onset. Until early 2026, nearly every target forecast.
     Between 2026-02-11 and 2026-02-26, about half the targets started carrying `i` points, and the
     forecast yield fell from about 95% to about 40%.
   - On 2026-11-12, 97 of 157 targets failed this way.
   - The losses are not random. Well-sampled sources are the ones with `i` points, so the survivors
     are biased toward sparse g/r-only light curves.

3. **The forecast clock runs 5 hours behind.** `Transient.__init__` defaults `current_mjd` to
   `Time(datetime.today()).mjd`. That is local wall-clock time read as UTC, so photometry taken in
   the last 5 hours is treated as future data and dropped. It hit 9 targets on 2026-11-12.
   `get_objects_antares.py` already uses `datetime.utcnow()`.

There is also a process gap. The deployed checkout has drifted from `refitt-forecast`, whose last
push was in 2021: five files in `forecast/` have uncommitted changes, including
`get_objects_antares.py`. A fix made only in the deployed checkout would be unreviewed and could
not be undone.

## Why it was deferred

This was found out of cycle, during a root-cause analysis of the empty target list on 2026-11-12.
All three defects predate that analysis. The pipeline lives in a different repository from REFITT,
and the GTF model will replace it. So the work is a salvage: keep science flowing for about a
month, and invest nothing in the pipeline beyond that.

## Outcome / vision

For the month until GTF lands, the daily run forecasts every target ANTARES sends, including
targets with `i`-band points. The first day the run receives no new sources or produces an empty
priority list, it sends an alert instead of failing silently. Every change is committed to
`refitt-forecast` and can be reverted.

## Sketch of the acceptance criteria

- **R1** — WHEN a target's light curve holds points in a band that `defs.antares_band_name_dict`
  does not map, the pipeline SHALL drop those points before forecasting, and forecast the target
  from its g and R points.
- **R2** — WHEN the run replays the saved 2026-11-12 inputs offline, each of the 97 targets that
  failed on `i`-band points SHALL produce a forecast, unless it has too few g/R points. Each
  target skipped for that reason SHALL be named with that reason.
- **R3** — WHEN the forecast fails, the run SHALL log the target ID and the actual exception, not
  the fixed "GP fit failed" line.
- **R4** — The forecast's current time SHALL be UTC.
- **R5** — WHEN a run finds no source first detected in the last 3 days, or writes an empty
  `priority.csv`, it SHALL send an alert through the existing `utils.email` path.
- **R6** — The deployed checkout's current state SHALL be committed to `refitt-forecast` before
  any change, and each fix SHALL land as its own revertible commit.

## Notes

- **Not code, and a prerequisite to any recovery:** get `refitt_newsources_snrcut` tagging again
  in ANTARES. Without new sources, R1–R4 only add forecasts for past-peak objects, and
  `priority.csv` can stay empty.
- **Non-goals:**
  - mapping `i` to band 3 or retraining for it (the kernel and its reference library are g/r only:
    `ZTF_public` → `[1, 2]`);
  - changing the ranking cuts;
  - touching the server, or GTF itself.
- **Verify cheaply:** replay saved run directories through `kernel.py` in a scratch copy. The
  repository keeps no test suite for this.
- **Related:** the GTF model that replaces this pipeline; the server's ingest of `priority.csv`
  (not inspected in this analysis).
- **Found by:** an out-of-cycle root-cause analysis of the 2026-11-12 run.
