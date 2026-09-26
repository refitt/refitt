"""The small, supported Python API for local host association."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .association import run_association
from .catalog import CatalogRegistry, PanStarrsLocalProvider, RegladeLocalProvider
from .schemas import AssociationOptions, AssociationResult, TransientInput


@dataclass(slots=True)
class HostAssociator:
    """A reusable, read-only associator for one or more local catalogs.

    Construct one instance per worker and call :meth:`find_host` for each
    transient. Catalog collections open lazily on the first search.
    """

    _registry: CatalogRegistry
    options: AssociationOptions = field(default_factory=AssociationOptions)

    @classmethod
    def ps1(cls, hats_path: str | Path, *, margin_cache_path: str | Path | None = None,
            options: AssociationOptions | None = None) -> "HostAssociator":
        provider = PanStarrsLocalProvider(hats_path, margin_cache_path=margin_cache_path)
        return cls(CatalogRegistry([provider]), options or AssociationOptions())

    @classmethod
    def regalade(cls, hats_path: str | Path, *, margin_cache_path: str | Path | None = None,
                options: AssociationOptions | None = None) -> "HostAssociator":
        provider = RegladeLocalProvider(hats_path, margin_cache_path=margin_cache_path)
        return cls(CatalogRegistry([provider]), options or AssociationOptions())

    @classmethod
    def local(cls, *, ps1_path: str | Path | None = None, ps1_margin_cache_path: str | Path | None = None,
              regalade_path: str | Path | None = None, regalade_margin_cache_path: str | Path | None = None,
              options: AssociationOptions | None = None) -> "HostAssociator":
        providers = []
        if ps1_path is not None:
            providers.append(PanStarrsLocalProvider(ps1_path, margin_cache_path=ps1_margin_cache_path))
        if regalade_path is not None:
            providers.append(RegladeLocalProvider(regalade_path, margin_cache_path=regalade_margin_cache_path))
        if not providers:
            raise ValueError("supply ps1_path, regalade_path, or both")
        return cls(CatalogRegistry(providers), options or AssociationOptions())

    def find_host(self, ra_deg: float, dec_deg: float, *, position_error_arcsec: float | None = None,
                  redshift: float | None = None) -> AssociationResult:
        """Find and rank host candidates for one sky position."""
        transient = TransientInput(ra_deg=ra_deg, dec_deg=dec_deg, position_error_arcsec=position_error_arcsec, redshift=redshift)
        return run_association(transient, self._registry, self.options)
