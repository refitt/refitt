"""Internal stages for local host association."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .astro_prost_math import AssociationCandidate, score_candidates, score_offset_samples
from .catalog import CatalogRegistry
from .morphology import find_ps1_shred_indices, median_grizy_kron_mag, sample_morphologies
from .schemas import AssociationOptions, AssociationResult, CatalogDetection, HostResult, Morphology, TransientInput


@dataclass(frozen=True, slots=True)
class _PreparedCandidate:
    """One catalog detection in the exact form required for scoring and output."""

    catalog_id: str
    detection: CatalogDetection
    morphology: Morphology
    photometry: dict[str, float | None]
    redshift: float | None
    redshift_err: float | None
    redshift_source: str | None
    apparent_mag: float | None
    apparent_mag_err: float | None


@dataclass(frozen=True, slots=True)
class _ScoredSamples:
    probabilities: np.ndarray  # (draws, candidates)
    null_draws: list[dict[str, float]]
    vectorized_offset_only: bool


def _catalog_id(detection: CatalogDetection) -> str:
    return detection.detection_id.removeprefix("PS1:") if detection.catalog == "PS1" else detection.detection_id


def _remove_ps1_shreds(candidates: list[_PreparedCandidate]) -> tuple[list[_PreparedCandidate], list[str]]:
    """Remove fainter PS1 extraction fragments before probability scoring."""
    if len(candidates) < 2:
        return candidates, []
    magnitudes = []
    for candidate in candidates:
        ps1_kron = {m.filter_id: m.magnitude for m in candidate.detection.measurements
                    if m.source_catalog == "PS1" and m.photometry_type == "kron"}
        magnitudes.append(median_grizy_kron_mag(ps1_kron))
    dropped = find_ps1_shred_indices(
        [item.detection.ra_deg for item in candidates], [item.detection.dec_deg for item in candidates],
        [item.morphology for item in candidates], magnitudes,
    )
    return ([item for index, item in enumerate(candidates) if index not in dropped],
            [candidates[index].catalog_id for index in sorted(dropped)])


def _prepare_candidates(detections: list[CatalogDetection]) -> tuple[list[_PreparedCandidate], list[str]]:
    prepared: list[_PreparedCandidate] = []
    for detection in detections:
        if detection.morphology is None:
            continue
        magnitudes = [m.magnitude for m in detection.measurements if m.magnitude is not None]
        errors = [m.magnitude_error for m in detection.measurements if m.magnitude_error is not None]
        prepared.append(_PreparedCandidate(
            catalog_id=_catalog_id(detection), detection=detection, morphology=detection.morphology,
            photometry={m.filter_id: m.magnitude for m in detection.measurements}, redshift=detection.redshift,
            redshift_err=detection.redshift_err, redshift_source=detection.catalog if detection.redshift is not None else None,
            apparent_mag=float(np.median(magnitudes)) if magnitudes else None,
            apparent_mag_err=float(np.median(errors)) if errors else None,
        ))
    return _remove_ps1_shreds(prepared)


def _score_offset_only(transient: TransientInput, candidates: list[_PreparedCandidate], options: AssociationOptions) -> _ScoredSamples:
    """Reproduce astro-prost's legacy draw order while scoring NumPy arrays."""
    rng = np.random.RandomState(options.seed)
    count = len(candidates)
    position_error = transient.position_error_arcsec or 0.1
    tra = rng.normal(transient.ra_deg, position_error / 3600.0, options.samples)
    tdec = rng.normal(transient.dec_deg, position_error / 3600.0, options.samples)
    a = np.asarray([item.morphology.a_arcsec for item in candidates])[:, None]
    a_std = np.asarray([item.morphology.sigma_a_arcsec for item in candidates])[:, None]
    ratio = np.asarray([item.morphology.a_arcsec / item.morphology.b_arcsec for item in candidates])[:, None]
    phi = np.radians(np.asarray([item.morphology.pa_deg for item in candidates]))[:, None]
    score = score_offset_samples(
        np.asarray([item.detection.ra_deg for item in candidates]), np.asarray([item.detection.dec_deg for item in candidates]), tra, tdec,
        rng.normal(a, a_std, (count, options.samples)),
        rng.normal(ratio, 0.05 * np.abs(ratio), (count, options.samples)),
        rng.normal(phi, np.maximum(1e-10, 0.05 * np.abs(phi)), (count, options.samples)),
    )
    return _ScoredSamples(score.probabilities.T,
        [{name: float(values[draw]) for name, values in score.nulls.items()} for draw in range(options.samples)], True)


def _score_with_optional_terms(transient: TransientInput, candidates: list[_PreparedCandidate], options: AssociationOptions) -> _ScoredSamples:
    sampled = [sample_morphologies(item.morphology, options.samples, options.seed + index) for index, item in enumerate(candidates)]
    probabilities: list[list[float]] = []
    null_draws: list[dict[str, float]] = []
    for draw in range(options.samples):
        draw_candidates = [AssociationCandidate(
            identity=item.catalog_id, ra_deg=item.detection.ra_deg, dec_deg=item.detection.dec_deg,
            a_arcsec=sampled[index][draw].a_arcsec, b_arcsec=sampled[index][draw].b_arcsec, pa_deg=sampled[index][draw].pa_deg,
            redshift=item.redshift, redshift_err=item.redshift_err, apparent_mag=item.apparent_mag,
            apparent_mag_err=item.apparent_mag_err,
        ) for index, item in enumerate(candidates)]
        score = score_candidates(
            transient.ra_deg, transient.dec_deg, draw_candidates, samples=1, seed=options.seed + draw,
            transient_redshift=transient.redshift, position_error_arcsec=transient.position_error_arcsec,
            limiting_magnitude=options.limiting_magnitude, use_redshift=options.use_redshift,
            use_magnitude=options.use_magnitude, search_radius_arcsec=options.search_radius_arcsec,
        )
        probabilities.append(score.probabilities.tolist())
        null_draws.append(score.nulls)
    return _ScoredSamples(np.asarray(probabilities), null_draws, False)


def _score_candidates(transient: TransientInput, candidates: list[_PreparedCandidate], options: AssociationOptions) -> _ScoredSamples:
    return _score_offset_only(transient, candidates, options) if not options.use_redshift and not options.use_magnitude else _score_with_optional_terms(transient, candidates, options)


def _mean_null_hypotheses(draws: list[dict[str, float]]) -> dict[str, float]:
    return {name: float(np.mean([draw[name] for draw in draws if name in draw])) for name in {name for draw in draws for name in draw}}


def _nominal_dlr(transient: TransientInput, candidate: _PreparedCandidate) -> float:
    """Return the transient offset in units of the candidate's nominal DLR."""
    morphology = candidate.morphology
    dra = math.radians((transient.ra_deg - candidate.detection.ra_deg + 180.0) % 360.0 - 180.0)
    ddec = math.radians(transient.dec_deg - candidate.detection.dec_deg)
    dec = math.radians((transient.dec_deg + candidate.detection.dec_deg) / 2.0)
    offset_arcsec = math.degrees(math.hypot(dra * math.cos(dec), ddec)) * 3600.0
    gamma = math.atan2((transient.ra_deg - candidate.detection.ra_deg) * 3600.0,
                       (transient.dec_deg - candidate.detection.dec_deg) * 3600.0)
    ratio = morphology.a_arcsec / morphology.b_arcsec
    radius = morphology.a_arcsec / math.hypot(
        ratio * math.sin(math.radians(morphology.pa_deg) - gamma),
        math.cos(math.radians(morphology.pa_deg) - gamma),
    )
    return offset_arcsec / radius


def _result_candidates(transient: TransientInput, candidates: list[_PreparedCandidate], probabilities: np.ndarray) -> list[HostResult]:
    result = [HostResult(
        catalog=item.detection.catalog, catalog_id=item.catalog_id,
        ra_deg=item.detection.ra_deg, dec_deg=item.detection.dec_deg, morphology=item.morphology,
        dlr=_nominal_dlr(transient, item),
        redshift=item.redshift, redshift_err=item.redshift_err, redshift_source=item.redshift_source,
        posterior_mean=float(probabilities[:, index].mean()), posterior_std=float(probabilities[:, index].std()),
        selection_frequency=float((probabilities[:, index] == probabilities.max(axis=1)).mean()),
    ) for index, item in enumerate(candidates)]
    return sorted(result, key=lambda item: item.posterior_mean, reverse=True)


def _select_outcome(candidates: list[HostResult], scoring_ids: list[str], scored: _ScoredSamples, nulls: dict[str, float]) -> tuple[str, HostResult | None]:
    if scored.vectorized_offset_only:
        null_arrays = [np.asarray([draw.get(name, 0.0) for draw in scored.null_draws]) for name in ("outside_cone", "unobserved", "hostless")]
        winner = int(np.bincount(np.argmax(np.column_stack((scored.probabilities, *null_arrays)), axis=1), minlength=len(candidates) + 3).argmax())
        if winner < len(candidates):
            winner_id = scoring_ids[winner]
            return "associated", next(item for item in candidates if item.catalog_id == winner_id)
        return ("hostless", None) if winner == len(candidates) + 2 else ("outside_catalog", None)
    best = candidates[0]
    if nulls.get("hostless", 0.0) >= best.posterior_mean:
        return "hostless", None
    if nulls.get("outside_cone", 0.0) >= best.posterior_mean:
        return "outside_catalog", None
    return "associated", best


def run_association(transient: TransientInput, registry: CatalogRegistry, options: AssociationOptions) -> AssociationResult:
    """Run the internal association workflow for a configured registry."""
    catalog_rows = registry.query(transient, options)
    candidates, _ = _prepare_candidates(catalog_rows.detections)
    if not candidates:
        return AssociationResult(outcome="no_candidates")
    scored = _score_candidates(transient, candidates, options)
    nulls = _mean_null_hypotheses(scored.null_draws)
    results = _result_candidates(transient, candidates, scored.probabilities)
    outcome, host = _select_outcome(results, [item.catalog_id for item in candidates], scored, nulls)
    return AssociationResult(outcome=outcome, host=host)
