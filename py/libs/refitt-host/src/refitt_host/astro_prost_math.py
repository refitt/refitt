"""Catalog-independent host-association mathematics.

This module is a clean-room, small-scope port of the numerical association
path in astro-prost 1.2.13 (MIT License, Copyright Alexander Gagliano and
contributors).  It deliberately contains no catalog names, table schemas, or
network access.  The port uses a caller supplied ``numpy.random.Generator`` so
an association is reproducible for a configured seed.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
from scipy.special import gammaln

PROB_FLOOR = np.finfo(float).eps
RAD_TO_ARCSEC = 206265.0


@dataclass(frozen=True)
class AssociationCandidate:
    """The catalog-neutral inputs required by the association equations."""

    identity: str
    ra_deg: float
    dec_deg: float
    a_arcsec: float
    b_arcsec: float
    pa_deg: float
    sigma_a_arcsec: float = 0.05
    sigma_b_arcsec: float = 0.05
    redshift: float | None = None
    redshift_err: float | None = None
    apparent_mag: float | None = None
    apparent_mag_err: float | None = None


@dataclass(frozen=True)
class ScoreResult:
    probabilities: np.ndarray
    nulls: dict[str, float]
    terms: tuple[str, ...]


@dataclass(frozen=True)
class SampleScoreResult:
    """Per-draw normalized posteriors for the vectorized offset-only path."""

    probabilities: np.ndarray  # (candidates, draws)
    nulls: dict[str, np.ndarray]


def _normal_pdf(x: np.ndarray, loc: np.ndarray | float, scale: np.ndarray | float) -> np.ndarray:
    scale = np.maximum(np.asarray(scale, dtype=float), PROB_FLOOR)
    value = (np.asarray(x, dtype=float) - loc) / scale
    return np.exp(-0.5 * value * value) / (math.sqrt(2.0 * math.pi) * scale)


def _offset_density(x: np.ndarray) -> np.ndarray:
    """astro-prost's uniform [0, 10] offset prior times Gamma(0.75) like."""
    x = np.asarray(x, dtype=float)
    prior = np.where((x >= 0.0) & (x <= 10.0), 0.1, 0.0)
    positive = np.maximum(x, PROB_FLOOR)
    # gamma.pdf(x, a=.75, scale=1), written locally to avoid distribution state.
    like = np.exp(-positive + (-0.25 * np.log(positive)) - gammaln(0.75))
    return prior * like


def _redshift_prior(z: np.ndarray) -> np.ndarray:
    # astro-prost demo/default convention: half-normal z prior, scale 0.5,
    # with the tiny positive floor used by its candidate builders.
    z = np.maximum(np.asarray(z, dtype=float), 0.001)
    return math.sqrt(2.0 / math.pi) / 0.5 * np.exp(-0.5 * (z / 0.5) ** 2)


def _magnitude_density(absolute_mag: np.ndarray) -> np.ndarray:
    # The upstream default prior is uniform [-30, -10].  SnRateAbsmag is a
    # luminosity weighting; 10**(-0.4 M) is its stable proportional form.
    m = np.asarray(absolute_mag, dtype=float)
    return np.where((m >= -30.0) & (m <= -10.0), 10.0 ** (-0.4 * (m + 30.0)) / 20.0, 0.0)


def _separation_arcsec(ra1: np.ndarray, dec1: np.ndarray, ra2: np.ndarray, dec2: np.ndarray) -> np.ndarray:
    # Small cone tangent-plane form is what astro-prost's calc_dlr uses for
    # its directional radius; great-circle separation is used for offsets.
    dra = np.radians((ra1 - ra2 + 180.0) % 360.0 - 180.0)
    d1, d2 = np.radians(dec1), np.radians(dec2)
    angle = 2.0 * np.arcsin(np.sqrt(np.sin((d1 - d2) / 2.0) ** 2 + np.cos(d1) * np.cos(d2) * np.sin(dra / 2.0) ** 2))
    return np.degrees(angle) * 3600.0


def score_candidates(
    ra_deg: float, dec_deg: float, candidates: Sequence[AssociationCandidate], *,
    samples: int, seed: int, position_error_arcsec: float | None = None,
    transient_redshift: float | None = None, limiting_magnitude: float | None = None,
    use_redshift: bool = True, use_magnitude: bool = True, search_radius_arcsec: float = 60.0,
) -> ScoreResult:
    """Score a common candidate set and return mean posteriors and null terms.

    A term is enabled only if every candidate can support it.  This is the
    important difference from letting a richer catalog quietly receive an
    extra advantage in a mixed-catalog query.
    """
    if not candidates:
        return ScoreResult(np.empty(0), {"outside_cone": PROB_FLOOR, "unobserved": PROB_FLOOR, "hostless": PROB_FLOOR}, ("offset",))
    rng = np.random.default_rng(seed)
    n, draws = len(candidates), int(samples)
    pos_err = 0.1 if position_error_arcsec is None else float(position_error_arcsec)
    tra = rng.normal(ra_deg, pos_err / 3600.0, draws)
    tdec = rng.normal(dec_deg, pos_err / 3600.0, draws)
    a = np.array([c.a_arcsec for c in candidates])[:, None]
    b = np.array([c.b_arcsec for c in candidates])[:, None]
    sa = np.array([max(c.sigma_a_arcsec, PROB_FLOOR) for c in candidates])[:, None]
    sb = np.array([max(c.sigma_b_arcsec, PROB_FLOOR) for c in candidates])[:, None]
    sampled_a = np.maximum(rng.normal(a, sa, (n, draws)), PROB_FLOOR)
    sampled_b = np.maximum(rng.normal(b, sb, (n, draws)), PROB_FLOOR)
    phi = rng.normal(np.radians([c.pa_deg for c in candidates])[:, None], 0.05, (n, draws))
    cra = np.array([c.ra_deg for c in candidates])[:, None]
    cdec = np.array([c.dec_deg for c in candidates])[:, None]
    offset = _separation_arcsec(cra, cdec, tra[None, :], tdec[None, :])
    xr, yr = (tra[None, :] - cra) * 3600.0, (tdec[None, :] - cdec) * 3600.0
    gamma = np.arctan2(xr, yr)
    axis_ratio = sampled_a / sampled_b
    dlr = sampled_a / np.sqrt((axis_ratio * np.sin(phi - gamma)) ** 2 + np.cos(phi - gamma) ** 2)
    post = _offset_density(offset / np.maximum(dlr, PROB_FLOOR))
    terms = ["offset"]
    has_z = use_redshift and transient_redshift is not None and all(c.redshift is not None and c.redshift_err is not None and c.redshift_err > 0 for c in candidates)
    if has_z:
        z = rng.normal(np.array([c.redshift for c in candidates])[:, None], np.array([c.redshift_err for c in candidates])[:, None], (n, draws))
        z = np.maximum(z, 0.001)
        post *= _redshift_prior(z) * _normal_pdf(float(transient_redshift), z, np.array([c.redshift_err for c in candidates])[:, None])
        terms.append("redshift")
    has_mag = has_z and use_magnitude and limiting_magnitude is not None and all(c.apparent_mag is not None and c.apparent_mag_err is not None and c.apparent_mag_err > 0 for c in candidates)
    if has_mag:
        mag = rng.normal(np.array([c.apparent_mag for c in candidates])[:, None], np.array([c.apparent_mag_err for c in candidates])[:, None], (n, draws))
        # Low-z Hubble-law distance modulus is sufficient here and avoids an
        # implicit cosmology/catalog dependency in this isolated math module.
        dm = 5.0 * np.log10(np.maximum(299792.458 * np.maximum(z, .001) / 70.0, .001) * 1e6 / 10.0)
        post *= _magnitude_density(mag - dm)
        terms.append("magnitude")
    hostless = np.full(draws, PROB_FLOOR)
    outside = np.full(draws, PROB_FLOOR)
    unobserved = np.full(draws, PROB_FLOOR)
    # astro-prost only gives meaningful outside/unobserved models when the
    # corresponding redshift/magnitude capability exists. Unsupported terms
    # intentionally retain its numerical floor.
    if has_z:
        outside = np.full(draws, float(np.mean(_offset_density(np.full(draws, 5.0)))) * PROB_FLOOR)
    if has_mag:
        unobserved = np.full(draws, float(np.mean(_magnitude_density(np.full(draws, -10.0)))) * PROB_FLOOR)
    total = np.maximum(np.sum(post, axis=0) + hostless + outside + unobserved, PROB_FLOOR)
    normalized = post / total
    return ScoreResult(np.mean(normalized, axis=1), {
        "outside_cone": float(np.mean(outside / total)),
        "unobserved": float(np.mean(unobserved / total)),
        "hostless": float(np.mean(hostless / total)),
    }, tuple(terms))


def score_offset_samples(
    candidate_ra_deg: np.ndarray, candidate_dec_deg: np.ndarray,
    transient_ra_deg: np.ndarray, transient_dec_deg: np.ndarray,
    a_arcsec: np.ndarray, axis_ratio: np.ndarray, phi_rad: np.ndarray,
) -> SampleScoreResult:
    """Vectorized offset/DLR posterior for pre-sampled astro-prost inputs.

    All sampled arrays are shaped ``(n_candidates, n_draws)`` except the
    transient positions, which are ``(n_draws,)``.  Sampling is deliberately
    outside this function: that lets the caller reproduce astro-prost's
    legacy RandomState draw order exactly while retaining a vectorized score.
    """
    a = np.maximum(np.asarray(a_arcsec, dtype=float), PROB_FLOOR)
    n, draws = a.shape
    ratio = np.asarray(axis_ratio, dtype=float)
    phi = np.asarray(phi_rad, dtype=float)
    if ratio.shape != (n, draws) or phi.shape != (n, draws):
        raise ValueError("ellipse sample arrays must share the (candidates, draws) shape")
    tra = np.asarray(transient_ra_deg, dtype=float)
    tdec = np.asarray(transient_dec_deg, dtype=float)
    if tra.shape != (draws,) or tdec.shape != (draws,):
        raise ValueError("transient sample arrays must have one value per draw")
    cra = np.asarray(candidate_ra_deg, dtype=float)[:, None]
    cdec = np.asarray(candidate_dec_deg, dtype=float)[:, None]
    offset = _separation_arcsec(cra, cdec, tra[None, :], tdec[None, :])
    gamma = np.arctan2((tra[None, :] - cra) * 3600.0, (tdec[None, :] - cdec) * 3600.0)
    dlr = a / np.sqrt((ratio * np.sin(phi - gamma)) ** 2 + np.cos(phi - gamma) ** 2)
    post = _offset_density(offset / np.maximum(dlr, PROB_FLOOR))
    hostless = np.full(draws, PROB_FLOOR)
    outside = np.full(draws, PROB_FLOOR)
    unobserved = np.full(draws, PROB_FLOOR)
    total = np.maximum(np.sum(post, axis=0) + hostless + outside + unobserved, PROB_FLOOR)
    return SampleScoreResult(post / total, {
        "outside_cone": outside / total,
        "unobserved": unobserved / total,
        "hostless": hostless / total,
    })
