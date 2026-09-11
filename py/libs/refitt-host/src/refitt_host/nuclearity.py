"""Optional, best-effort iinuclear checks independent of host association."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import NuclearityResult


def check_nuclearity(ztf_id: str, *, output_dir: str | Path = "refitt-host-output") -> NuclearityResult:
    """Check one named transient with iinuclear.

    This is independent of host association and deliberately accepts the only
    identifier iinuclear uses, rather than exposing internal input models.
    """
    return _check_nuclearity(ztf_id.strip(), Path(output_dir))


def _check_nuclearity(ztf_id: str, output_dir: Path) -> NuclearityResult:
    """Run iinuclear's positional test when available.

    ``nuclearity_p_value`` is the test p-value, not a Bayesian probability.
    Any third-party service failure becomes a structured unavailable result.
    """
    if not ztf_id:
        return NuclearityResult(status="not_requested")
    try:
        import iinuclear  # type: ignore
        output_dir.mkdir(parents=True, exist_ok=True)
        result: Any = iinuclear.isit(ztf_id, save_all=False, base_dir=str(output_dir), plot=False)
        if result is None:
            return NuclearityResult(status="unavailable", failure_detail="iinuclear found no cataloged galaxy")
        _, chi, p, is_nuclear, *_ = result
        return NuclearityResult(status="success",
                                nuclearity_p_value=None if p is None else float(p),
                                chi_square=None if chi is None else float(chi),
                                is_nuclear=None if is_nuclear is None else bool(is_nuclear))
    except Exception as exc:  # iinuclear calls several external services
        return NuclearityResult(status="unavailable", failure_detail=f"iinuclear unavailable: {type(exc).__name__}: {exc}")
