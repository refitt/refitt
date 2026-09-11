"""Tests for the PS1 local-catalog adapter."""
from __future__ import annotations

import sys
import types

import pytest

from refitt_host.catalog import PanStarrsLocalProvider
from refitt_host.schemas import AssociationOptions, TransientInput

_RA, _DEC = 321.8157, 3.7980


def _ps1_row(**overrides):
    row = {"objID": "123456789", "raMean": _RA, "decMean": _DEC, "z_phot0": 0.0325, "z_photErr": 0.01,
           "extrapolation_Photoz": 0, "a_arcsec": 2.0, "b_arcsec": 1.88, "pa_deg": 45.0}
    row.update(overrides)
    return row


def test_provider_requires_an_absolute_catalog_path():
    with pytest.raises(ValueError, match="absolute"):
        PanStarrsLocalProvider("relative/catalog")


def test_search_builds_detection_with_precomputed_morphology_and_redshift():
    provider = PanStarrsLocalProvider("/tmp/ps1", query_rows=lambda transient, options: [_ps1_row()])
    detections = provider.search_detections(TransientInput(ra_deg=_RA, dec_deg=_DEC), AssociationOptions())
    assert len(detections) == 1
    assert detections[0].morphology_quality == "ps1_moment"
    assert detections[0].morphology.a_arcsec == pytest.approx(2.0)
    assert detections[0].redshift == pytest.approx(0.0325)


def test_sigma_is_derived_from_options():
    provider = PanStarrsLocalProvider("/tmp/ps1", query_rows=lambda transient, options: [_ps1_row(a_arcsec=0.4, b_arcsec=0.2)])
    options = AssociationOptions(sigma_size_fraction=0.05)
    detection = provider.search_detections(TransientInput(ra_deg=_RA, dec_deg=_DEC), options)[0]
    assert detection.morphology.sigma_a_arcsec == pytest.approx(max(0.05 * 0.4, options.shape_floor))


def test_lsdb_catalog_is_opened_once_across_many_queries(monkeypatch):
    calls = []

    class FakeCatalog:
        def cone_search(self, ra_deg, dec_deg, radius_arcsec):
            return self

    def read_hats(uri, columns=None):
        calls.append(uri)
        return FakeCatalog()

    monkeypatch.setitem(sys.modules, "lsdb", types.SimpleNamespace(read_hats=read_hats))
    monkeypatch.setattr("refitt_host.catalog._as_records", lambda selected, columns: [_ps1_row()])
    provider = PanStarrsLocalProvider("/tmp/ps1")
    transient = TransientInput(ra_deg=_RA, dec_deg=_DEC)
    for _ in range(5):
        assert len(provider.search_detections(transient, AssociationOptions())) == 1
    assert calls == ["/tmp/ps1"]
