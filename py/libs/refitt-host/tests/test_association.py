import pytest

from refitt_host import AssociationOptions, HostAssociator
from refitt_host.association import run_association
from refitt_host.catalog import CatalogRegistry, CatalogRows, CatalogSpec
from refitt_host.schemas import CatalogDetection, Measurement, Morphology, TransientInput


def test_host_associator_is_reusable(monkeypatch):
    calls = []
    monkeypatch.setattr("refitt_host.api.run_association", lambda transient, registry, options: calls.append((transient, registry, options)) or "result")
    hosts = HostAssociator.ps1("/tmp/ps1", options=AssociationOptions(samples=64, seed=11))
    assert hosts.find_host(10.0, -2.0, position_error_arcsec=0.3, redshift=0.02) == "result"
    assert calls[0][0].redshift == 0.02
    assert calls[0][2].samples == 64


def test_local_requires_at_least_one_catalog():
    with pytest.raises(ValueError, match="supply"):
        HostAssociator.local()


def test_magnitude_scoring_requires_redshift_scoring():
    with pytest.raises(ValueError, match="requires"):
        AssociationOptions(use_magnitude=True)


def _provider(detections):
    class Provider:
        spec = CatalogSpec("fixture")

        def search(self, transient, options):
            return CatalogRows(detections)
    return Provider()


def test_redshift_term_rejects_mismatched_transient_redshift():
    morph = Morphology(a_arcsec=9.68, b_arcsec=4.04, pa_deg=56.0, sigma_a_arcsec=1.3, sigma_b_arcsec=0.6)
    detection = CatalogDetection(detection_id="fixture:1", catalog="fixture", ra_deg=322.3035, dec_deg=2.9996,
                                 morphology=morph, morphology_quality="fixture", redshift=0.0325, redshift_err=0.001)
    registry = CatalogRegistry([_provider([detection])])
    options = AssociationOptions(samples=50, use_redshift=True)
    matching = run_association(TransientInput(ra_deg=322.3035, dec_deg=2.9996, redshift=0.0325), registry, options)
    mismatched = run_association(TransientInput(ra_deg=322.3035, dec_deg=2.9996, redshift=0.5), registry, options)
    assert matching.outcome == "associated"
    assert matching.host is not None
    assert mismatched.outcome == "hostless"


def test_shreds_are_removed_before_scoring():
    morph = Morphology(a_arcsec=3.0, b_arcsec=3.0, pa_deg=0.0, sigma_a_arcsec=0.1, sigma_b_arcsec=0.1)

    def measurements(detection_id, magnitude):
        return [Measurement(filter_id=f"PS1.{band}", magnitude=magnitude, source_catalog="PS1", source_detection_id=detection_id) for band in "gri"]

    bright = CatalogDetection(detection_id="PS1:1", catalog="PS1", ra_deg=10.0, dec_deg=0.0, morphology=morph,
                              morphology_quality="ps1_kron_circular", measurements=measurements("PS1:1", 19.0))
    shred = CatalogDetection(detection_id="PS1:2", catalog="PS1", ra_deg=10.0 + 1 / 3600, dec_deg=0.0, morphology=morph,
                             morphology_quality="ps1_kron_circular", measurements=measurements("PS1:2", 21.0))
    result = run_association(TransientInput(ra_deg=10.0, dec_deg=0.0), CatalogRegistry([_provider([bright, shred])]), AssociationOptions(samples=1))
    assert result.host is not None
    assert result.host.catalog_id == "1"
