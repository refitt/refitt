"""Public input and result models for host association."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SerializableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class TransientInput(SerializableModel):
    ra_deg: float = Field(ge=0.0, lt=360.0)
    dec_deg: float = Field(ge=-90.0, le=90.0)
    position_error_arcsec: float | None = Field(default=None, gt=0.0)
    redshift: float | None = Field(default=None, ge=0.0)


@dataclass(frozen=True, slots=True)
class AssociationOptions:
    """Scoring and query settings shared by every search from an associator.

    Catalog paths belong to :class:`refitt_host.HostAssociator`; this class
    contains only behavior a caller may reasonably tune per run.
    """

    search_radius_arcsec: float = 60.0
    samples: int = 1000
    seed: int = 1729
    limiting_magnitude: float | None = 22.0
    use_redshift: bool = False
    use_magnitude: bool = False
    verbose: bool = False
    sigma_size_fraction: float = 0.05
    shape_floor: float = 1e-10

    def __post_init__(self) -> None:
        if self.search_radius_arcsec <= 0 or self.samples <= 0:
            raise ValueError("search_radius_arcsec and samples must be positive")
        if self.limiting_magnitude is not None and self.limiting_magnitude <= 0:
            raise ValueError("limiting_magnitude must be positive when supplied")
        if self.sigma_size_fraction <= 0 or self.shape_floor <= 0:
            raise ValueError("morphology uncertainty floors must be positive")
        if self.use_magnitude and not self.use_redshift:
            raise ValueError("use_magnitude requires use_redshift")


class Morphology(SerializableModel):
    a_arcsec: float = Field(gt=0.0)
    b_arcsec: float = Field(gt=0.0)
    pa_deg: float
    sigma_a_arcsec: float = Field(gt=0.0)
    sigma_b_arcsec: float = Field(gt=0.0)


class Measurement(SerializableModel):
    """The optional Kron magnitude carried by a local catalog detection."""

    filter_id: str
    photometry_type: Literal["kron"] = "kron"
    source_catalog: str
    source_detection_id: str
    magnitude: float | None = None
    magnitude_error: float | None = Field(default=None, ge=0.0)


class CatalogDetection(SerializableModel):
    """A single catalog row, retaining its native identity."""

    detection_id: str
    catalog: str
    release: str | None = None
    ra_deg: float = Field(ge=0.0, lt=360.0)
    dec_deg: float = Field(ge=-90.0, le=90.0)
    ra_error_arcsec: float | None = Field(default=None, gt=0.0)
    dec_error_arcsec: float | None = Field(default=None, gt=0.0)
    ra_dec_correlation: float | None = Field(default=None, ge=-1.0, le=1.0)
    morphology: Morphology | None = None
    morphology_quality: str = "unavailable"
    measurements: list[Measurement] = Field(default_factory=list)
    flags: tuple[str, ...] = ()
    # Optional local catalog redshift inputs for the common scoring terms.
    redshift: float | None = None
    redshift_err: float | None = Field(default=None, ge=0.0)


class HostResult(SerializableModel):
    """The single selected host returned to package users."""

    catalog: str
    catalog_id: str
    ra_deg: float
    dec_deg: float
    morphology: Morphology
    dlr: float | None = None
    posterior_mean: float = 0.0
    posterior_std: float = 0.0
    selection_frequency: float = 0.0
    redshift: float | None = None
    redshift_err: float | None = Field(default=None, ge=0.0)
    redshift_source: str | None = None


class NuclearityResult(SerializableModel):
    status: Literal["not_requested", "unavailable", "success"]
    nuclearity_p_value: float | None = None
    chi_square: float | None = None
    is_nuclear: bool | None = None
    galaxy_center_ra_deg: float | None = None
    galaxy_center_dec_deg: float | None = None
    galaxy_center_error_arcsec: float | None = None
    diagnostics_path: str | None = None
    failure_detail: str | None = None


class AssociationResult(SerializableModel):
    outcome: Literal["associated", "hostless", "outside_catalog", "no_candidates"]
    host: HostResult | None = None
