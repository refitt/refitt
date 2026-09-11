"""Read-only adapters for the project's local HATS catalogs."""
from __future__ import annotations

from contextlib import nullcontext, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .errors import CatalogQueryError, CatalogSchemaError
from .schemas import AssociationOptions, CatalogDetection, Measurement, Morphology, TransientInput


def _absolute_path(value: str | Path, name: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"{name} must be an absolute path")
    return path


@dataclass(frozen=True)
class CatalogRows:
    """Normalized local detections."""

    detections: list[CatalogDetection]


@dataclass(frozen=True)
class CatalogSpec:
    name: str
    role: str = "imaging"
    contains: Callable[[float, float], bool] = lambda ra, dec: True


class CatalogProvider(Protocol):
    spec: CatalogSpec
    def search(self, transient: TransientInput, options: AssociationOptions) -> CatalogRows: ...


class CatalogRegistry:
    """Explicitly registered local adapters; never a network fallback."""

    def __init__(self, providers: Sequence[CatalogProvider] = ()) -> None:
        self._providers: dict[str, CatalogProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: CatalogProvider) -> None:
        self._providers[provider.spec.name] = provider

    def query(self, transient: TransientInput, options: AssociationOptions) -> CatalogRows:
        detections: list[CatalogDetection] = []
        selected = [provider for provider in self._providers.values() if provider.spec.contains(transient.ra_deg, transient.dec_deg)]
        for provider in selected:
            try:
                result = provider.search(transient, options)
                detections.extend(result.detections)
            except CatalogQueryError as exc:  # One unavailable catalog must not lose another's candidates.
                continue
        return CatalogRows(detections)


def _as_records(frame: Any, columns: tuple[str, ...]) -> list[dict[str, Any]]:
    if hasattr(frame, "compute"):
        frame = frame.compute()
    if hasattr(frame, "to_pandas"):
        frame = frame.to_pandas()
    if hasattr(frame, "to_dict"):
        return [{key: value for key, value in row.items() if key in columns} for row in frame.to_dict(orient="records")]
    if isinstance(frame, list):
        return [{key: value for key, value in row.items() if key in columns} for row in frame]
    raise CatalogSchemaError("LSDB query result cannot be converted to records")


def _query_records(frame: Any, columns: tuple[str, ...], *, verbose: bool) -> list[dict[str, Any]]:
    """Materialize an LSDB query without progress output unless requested."""
    output = nullcontext() if verbose else redirect_stdout(StringIO())
    errors = nullcontext() if verbose else redirect_stderr(StringIO())
    with output, errors:
        return _as_records(frame, columns)


def _number(row: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        try:
            value = float(row.get(name))
        except (TypeError, ValueError):
            continue
        if value == value and value > -999:
            return value
    return None


class RegladeLocalProvider:
    """Read-only REGLADE adapter: distance-derived redshift and ellipse only."""

    spec = CatalogSpec("REGLADE")
    columns = ("ID", "ra", "dec", "D", "D_err", "R1", "R2", "PA", "flag")

    def __init__(self, hats_path: str | Path, *, margin_cache_path: str | Path | None = None,
                 query_rows: Callable[[TransientInput, AssociationOptions], list[dict[str, Any]]] | None = None) -> None:
        self.hats_path = _absolute_path(hats_path, "hats_path")
        self.margin_cache_path = None if margin_cache_path is None else _absolute_path(margin_cache_path, "margin_cache_path")
        self.query_rows = query_rows
        self._catalog: Any | None = None
        self._catalog_path: str | None = None

    def search(self, transient: TransientInput, options: AssociationOptions) -> CatalogRows:
        return CatalogRows(self.search_detections(transient, options))

    def search_detections(self, transient: TransientInput, options: AssociationOptions) -> list[CatalogDetection]:
        rows = self.query_rows(transient, options) if self.query_rows else self._rows(transient, options)
        detections: list[CatalogDetection] = []
        for row in rows:
            if str(row.get("low_reliability", row.get("flag", False))).strip().lower() in {"1", "true", "yes", "low", "bad"}:
                continue
            ra, dec = _number(row, "ra", "RA", "ra_deg"), _number(row, "dec", "DEC", "dec_deg")
            a, b = _number(row, "R1", "r1", "a_arcsec"), _number(row, "R2", "r2", "b_arcsec")
            if None in (ra, dec, a, b) or a <= 0 or b <= 0:
                continue
            distance, distance_err = _number(row, "D", "distance"), _number(row, "D_err", "distance_err")
            redshift = distance * 70.0 / 299792.458 if distance is not None else None
            redshift_err = abs(distance_err * 70.0 / 299792.458) if distance_err is not None else None
            identifier = str(row.get("ID", row.get("id", len(detections))))
            sigma = max(options.sigma_size_fraction * a, options.shape_floor)
            detections.append(CatalogDetection(
                detection_id=f"REGLADE:{identifier}", catalog="REGLADE", release="REGLADE", ra_deg=ra, dec_deg=dec,
                redshift=redshift, redshift_err=redshift_err,
                morphology=Morphology(a_arcsec=a, b_arcsec=b, pa_deg=_number(row, "PA", "pa") or 0.0,
                                      sigma_a_arcsec=sigma, sigma_b_arcsec=sigma), morphology_quality="regalade_r1_r2",
            ))
        return detections

    def _rows(self, transient: TransientInput, options: AssociationOptions) -> list[dict[str, Any]]:
        try:
            import lsdb  # type: ignore
        except ImportError as exc:
            raise CatalogQueryError("LSDB is required for local REGLADE queries; install refitt-host[hats]") from exc
        path = str(self.hats_path)
        if self._catalog is None or self._catalog_path != path:
            kwargs: dict[str, Any] = {"columns": list(self.columns)}
            if self.margin_cache_path is not None:
                kwargs["margin_cache"] = str(self.margin_cache_path)
            self._catalog = lsdb.read_hats(path, **kwargs)
            self._catalog_path = path
        try:
            return _query_records(self._catalog.cone_search(transient.ra_deg, transient.dec_deg, options.search_radius_arcsec), self.columns,
                                  verbose=options.verbose)
        except Exception as exc:
            raise CatalogQueryError(f"Local REGLADE cone query failed at {path}: {exc}") from exc


class PanStarrsLocalProvider:
    """Read-only local PS1 HATS adapter with precomputed ellipse and Kron magnitude."""

    spec = CatalogSpec("PS1", contains=lambda ra, dec: dec >= -30.0)

    columns = ("objID", "raMean", "decMean", "z_phot0", "z_photErr", "extrapolation_Photoz",
               "a_arcsec", "b_arcsec", "pa_deg", "kron_mag_median")

    def __init__(self, hats_path: str | Path, *, margin_cache_path: str | Path | None = None,
                 query_rows: Callable[[TransientInput, AssociationOptions], list[dict[str, Any]]] | None = None) -> None:
        self.hats_path = _absolute_path(hats_path, "hats_path")
        self.margin_cache_path = None if margin_cache_path is None else _absolute_path(margin_cache_path, "margin_cache_path")
        self.query_rows = query_rows
        self._catalog: Any | None = None
        self._catalog_path: str | None = None

    def search(self, transient: TransientInput, options: AssociationOptions) -> CatalogRows:
        return CatalogRows(self.search_detections(transient, options))

    def search_detections(self, transient: TransientInput, options: AssociationOptions) -> list[CatalogDetection]:
        rows = self.query_rows(transient, options) if self.query_rows else self._rows(transient, options)
        return [self._detection(row, options) for row in rows]

    def _rows(self, transient: TransientInput, options: AssociationOptions) -> list[dict[str, Any]]:
        try:
            import lsdb  # type: ignore
        except ImportError as exc:
            raise CatalogQueryError("LSDB is required for local PS1 queries; install refitt-host[hats]") from exc
        path = str(self.hats_path)
        if self._catalog is None or self._catalog_path != path:
            kwargs: dict[str, Any] = {"columns": list(self.columns)}
            if self.margin_cache_path is not None:
                kwargs["margin_cache"] = str(self.margin_cache_path)
            self._catalog = lsdb.read_hats(path, **kwargs)
            self._catalog_path = path
        try:
            return _query_records(self._catalog.cone_search(transient.ra_deg, transient.dec_deg, options.search_radius_arcsec), self.columns,
                                  verbose=options.verbose)
        except Exception as exc:
            raise CatalogQueryError(f"Local PS1 cone query failed at {path}: {exc}") from exc

    def _detection(self, row: Mapping[str, Any], options: AssociationOptions) -> CatalogDetection:
        a, b = float(row["a_arcsec"]), float(row["b_arcsec"])
        sigma_a = _number(row, "sigma_a_arcsec") or max(options.sigma_size_fraction * a, options.shape_floor)
        sigma_b = _number(row, "sigma_b_arcsec") or max(options.sigma_size_fraction * a, options.shape_floor)
        identifier = str(row["objID"])
        magnitude, magnitude_err = _number(row, "kron_mag_median"), _number(row, "kron_mag_err", "KronMagErr")
        measurements = [] if magnitude is None else [Measurement(filter_id="PS1.median", magnitude=magnitude,
            magnitude_error=magnitude_err, photometry_type="kron", source_catalog="PS1", source_detection_id=f"PS1:{identifier}")]
        return CatalogDetection(
            detection_id=f"PS1:{identifier}", catalog="PS1", release="local PS1 HATS", ra_deg=float(row["raMean"]), dec_deg=float(row["decMean"]),
            morphology=Morphology(a_arcsec=a, b_arcsec=b, pa_deg=float(row["pa_deg"]), sigma_a_arcsec=sigma_a, sigma_b_arcsec=sigma_b),
            morphology_quality="ps1_moment", redshift=_number(row, "z_phot0"), redshift_err=_number(row, "z_photErr"),
            measurements=measurements,
        )
