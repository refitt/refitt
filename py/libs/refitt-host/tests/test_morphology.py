from refitt_host.schemas import Morphology
from refitt_host.morphology import find_ps1_shred_indices, median_grizy_kron_mag, sample_morphologies

def test_sampling_is_deterministic_and_positive():
    shape = Morphology(a_arcsec=2, b_arcsec=1, pa_deg=0, sigma_a_arcsec=.1, sigma_b_arcsec=.1)
    assert sample_morphologies(shape, 3, 7) == sample_morphologies(shape, 3, 7)

def test_kron_median_and_shred_rejection():
    assert median_grizy_kron_mag({"g": 20., "r": 19., "i": 21.}) == 20.
    shape = Morphology(a_arcsec=3, b_arcsec=3, pa_deg=0, sigma_a_arcsec=.1, sigma_b_arcsec=.1)
    assert find_ps1_shred_indices([10., 10.+1/3600], [0., 0.], [shape, shape], [19., 21.]) == {1}
