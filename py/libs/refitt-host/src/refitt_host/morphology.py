"""Runtime morphology sampling and PS1 shred rejection."""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence
import numpy as np
from .schemas import Morphology

def sample_morphologies(shape: Morphology, samples: int, seed: int) -> list[Morphology]:
    rng = np.random.default_rng(seed)
    a = np.maximum(rng.normal(shape.a_arcsec, shape.sigma_a_arcsec, samples), 1e-10)
    b = np.maximum(rng.normal(shape.b_arcsec, shape.sigma_b_arcsec, samples), 1e-10)
    return [Morphology(a_arcsec=float(max(x, y)), b_arcsec=float(min(x, y)), pa_deg=shape.pa_deg,
                       sigma_a_arcsec=shape.sigma_a_arcsec, sigma_b_arcsec=shape.sigma_b_arcsec)
            for x, y in zip(a, b, strict=True)]

def median_grizy_kron_mag(values: Mapping[str, float | None]) -> float | None:
    data = sorted(value for value in values.values() if value is not None)
    if not data: return None
    mid = len(data) // 2
    return data[mid] if len(data) % 2 else (data[mid - 1] + data[mid]) / 2.0

def _sep(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    return math.degrees(math.hypot(math.radians((ra2-ra1+180)%360-180)*math.cos(math.radians((dec1+dec2)/2)), math.radians(dec2-dec1))) * 3600

def _radius(toward_ra: float, toward_dec: float, ra: float, dec: float, shape: Morphology) -> float:
    gamma = math.atan2((toward_ra-ra)*3600, (toward_dec-dec)*3600)
    ratio = shape.a_arcsec / shape.b_arcsec
    return shape.a_arcsec / math.hypot(ratio * math.sin(math.radians(shape.pa_deg)-gamma), math.cos(math.radians(shape.pa_deg)-gamma))

def find_ps1_shred_indices(ra: Sequence[float], dec: Sequence[float], shapes: Sequence[Morphology], mags: Sequence[float | None]) -> set[int]:
    dropped: set[int] = set()
    for left in range(len(ra)):
        for right in range(left + 1, len(ra)):
            if mags[left] is None or mags[right] is None or left in dropped or right in dropped: continue
            close = _sep(ra[left], dec[left], ra[right], dec[right]) < _radius(ra[right], dec[right], ra[left], dec[left], shapes[left]) or _sep(ra[left], dec[left], ra[right], dec[right]) < _radius(ra[left], dec[left], ra[right], dec[right], shapes[right])
            if close: dropped.add(left if mags[left] > mags[right] else right)
    return dropped
