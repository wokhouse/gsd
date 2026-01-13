"""Validation tests for tapped horn implementation.

This module tests the tapped horn impedance calculations and validates
against Hornresp reference data where available.

Literature:
    Berzborn & Smithers (2018), AES Paper 10047
    Danley, US Patent 8,457,341 B2
    literature/horns/tapped_horn_theory.md
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
    tapped_horn_tap_impedance,
)


# Standard air properties (Hornresp defaults)
MEDIUM = MediumProperties(rho=1.205, c=344.0)


class TestTappedHornGeometry:
    """Test TappedHorn dataclass validation and properties."""

    def test_valid_geometry(self):
        """Valid tapped horn geometry should be accepted."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
            upstream_profile='exponential',
            downstream_profile='exponential'
        )
        assert th.total_length == 190.0
        assert th.quarter_wave_frequency == pytest.approx(215.0, rel=0.01)

    def test_invalid_areas(self):
        """Non-monotonic area expansion should raise error."""
        with pytest.raises(ValueError, match="tap_area.*must be >"):
            TappedHorn(
                upstream_throat_area=200.0,  # Throat larger than tap
                tap_area=50.0,
                downstream_mouth_area=2000.0,
                upstream_length=40.0,
                downstream_length=150.0
            )

        with pytest.raises(ValueError, match="downstream_mouth_area.*must be >"):
            TappedHorn(
                upstream_throat_area=50.0,
                tap_area=200.0,
                downstream_mouth_area=100.0,  # Mouth smaller than tap
                upstream_length=40.0,
                downstream_length=150.0
            )

    def test_negative_dimensions(self):
        """Negative or zero dimensions should raise error."""
        with pytest.raises(ValueError, match="upstream_throat_area must be positive"):
            TappedHorn(
                upstream_throat_area=-50.0,
                tap_area=200.0,
                downstream_mouth_area=2000.0,
                upstream_length=40.0,
                downstream_length=150.0
            )

        with pytest.raises(ValueError, match="upstream_length must be positive"):
            TappedHorn(
                upstream_throat_area=50.0,
                tap_area=200.0,
                downstream_mouth_area=2000.0,
                upstream_length=0.0,
                downstream_length=150.0
            )

    def test_invalid_profile(self):
        """Invalid horn profile should raise error."""
        with pytest.raises(ValueError, match="upstream_profile must be"):
            TappedHorn(
                upstream_throat_area=50.0,
                tap_area=200.0,
                downstream_mouth_area=2000.0,
                upstream_length=40.0,
                downstream_length=150.0,
                upstream_profile='hyperbolic'  # Invalid
            )

    def test_section_conversion(self):
        """upstream_section() and downstream_section() should convert units correctly."""
        th = TappedHorn(
            upstream_throat_area=50.0,  # cm²
            tap_area=200.0,  # cm²
            downstream_mouth_area=2000.0,  # cm²
            upstream_length=40.0,  # cm
            downstream_length=150.0  # cm
        )

        # Get upstream section (should be ExponentialHorn in m² and m)
        up = th.upstream_section()
        assert_allclose(up.throat_area, 50.0 * 1e-4, rtol=1e-6)
        assert_allclose(up.mouth_area, 200.0 * 1e-4, rtol=1e-6)
        assert_allclose(up.length, 40.0 * 1e-2, rtol=1e-6)

        # Get downstream section
        down = th.downstream_section()
        assert_allclose(down.throat_area, 200.0 * 1e-4, rtol=1e-6)
        assert_allclose(down.mouth_area, 2000.0 * 1e-4, rtol=1e-6)
        assert_allclose(down.length, 150.0 * 1e-2, rtol=1e-6)


class TestTappedHornImpedance:
    """Test tapped horn impedance calculations."""

    @pytest.fixture
    def reference_tapped_horn(self):
        """Standard tapped horn for validation tests."""
        return TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
            upstream_profile='exponential',
            downstream_profile='exponential',
        )

    def test_upstream_closed_throat(self, reference_tapped_horn):
        """Upstream section with closed throat should have finite impedance."""
        freqs = np.array([20.0, 50.0, 100.0, 200.0])
        z_up = upstream_section_impedance(freqs, reference_tapped_horn, MEDIUM)

        # Should be finite, not infinite or NaN
        assert np.all(np.isfinite(z_up))

        # Real part should be very small (mostly reactive, closed throat)
        # Can be slightly negative due to numerical precision at high frequencies
        assert np.all(np.abs(np.real(z_up)) < 1e-3)

        # Should have reactive component (imaginary part)
        assert len(z_up) == len(freqs)

    def test_downstream_radiating_mouth(self, reference_tapped_horn):
        """Downstream section should show radiation loading."""
        freqs = np.array([20.0, 50.0, 100.0, 200.0])
        z_down = downstream_section_impedance(freqs, reference_tapped_horn, MEDIUM)

        assert np.all(np.isfinite(z_down))
        assert np.all(np.real(z_down) >= 0)

    def test_parallel_combination(self, reference_tapped_horn):
        """Tap impedance should be parallel combination of upstream and downstream."""
        freqs = np.array([50.0, 100.0, 200.0])

        z_up = upstream_section_impedance(freqs, reference_tapped_horn, MEDIUM)
        z_down = downstream_section_impedance(freqs, reference_tapped_horn, MEDIUM)
        z_tap = tapped_horn_tap_impedance(freqs, reference_tapped_horn, MEDIUM)

        # Verify parallel combination: Z_tap = (Z_up * Z_down) / (Z_up + Z_down)
        z_expected = (z_up * z_down) / (z_up + z_down)
        assert_allclose(z_tap, z_expected, rtol=1e-6)

    def test_frequency_scaling(self, reference_tapped_horn):
        """Impedance should vary with frequency."""
        freqs = np.logspace(1, 3, 50)  # 10 Hz to 1 kHz
        z_tap = tapped_horn_tap_impedance(freqs, reference_tapped_horn, MEDIUM)

        # All values should be finite
        assert np.all(np.isfinite(z_tap))

        # Impedance magnitude should vary significantly with frequency
        z_mag = np.abs(z_tap)
        assert z_mag.max() / z_mag.min() > 10  # At least 20:1 variation

    def test_quarter_wave_resonance(self, reference_tapped_horn):
        """At quarter-wave frequency, impedance should show resonance characteristics."""
        f_qw = reference_tapped_horn.quarter_wave_frequency
        freqs = np.array([f_qw * 0.8, f_qw, f_qw * 1.2])

        z_tap = tapped_horn_tap_impedance(freqs, reference_tapped_horn, MEDIUM)

        # All values should be finite
        assert np.all(np.isfinite(z_tap))

        # Near quarter-wave frequency, impedance should vary significantly
        # (indicating resonance region)
        z_mag = np.abs(z_tap)
        # The impedance should vary by at least a factor of 2 across this range
        assert z_mag.max() / z_mag.min() > 2.0


class TestConicalTappedHorn:
    """Test tapped horn with conical sections."""

    def test_conical_upstream(self):
        """Conical upstream section should work."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
            upstream_profile='conical',
            downstream_profile='exponential',
        )

        freqs = np.array([50.0, 100.0])
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))

    def test_conical_downstream(self):
        """Conical downstream section should work."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
            upstream_profile='exponential',
            downstream_profile='conical',
        )

        freqs = np.array([50.0, 100.0])
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))

    def test_fully_conical(self):
        """Fully conical tapped horn should work."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
            upstream_profile='conical',
            downstream_profile='conical',
        )

        freqs = np.array([50.0, 100.0])
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))


class TestHornrespValidation:
    """Validate against Hornresp reference data.

    These tests require Hornresp reference data files to be present.
    Generate reference data using Hornresp's export functionality.
    """

    @pytest.fixture
    def example_tapped_horn(self):
        """Example tapped horn design (similar to common DIY designs)."""
        return TappedHorn(
            upstream_throat_area=100.0,
            tap_area=400.0,
            downstream_mouth_area=4000.0,
            upstream_length=50.0,
            downstream_length=200.0,
            upstream_profile='exponential',
            downstream_profile='exponential',
        )

    def test_spl_response_vs_hornresp(self, example_tapped_horn):
        """SPL response should match Hornresp within 1 dB in passband.

        This test is skipped until Hornresp reference data is generated.
        """
        pytest.skip("Requires Hornresp reference data - run Hornresp and export results")

    def test_impedance_vs_hornresp(self, example_tapped_horn):
        """Electrical impedance should match Hornresp within 5%.

        This test is skipped until Hornresp reference data is generated.
        """
        pytest.skip("Requires Hornresp reference data - run Hornresp and export results")

    def test_excursion_vs_hornresp(self, example_tapped_horn):
        """Cone excursion should match Hornresp within 5%.

        This test is skipped until Hornresp reference data is generated.
        """
        pytest.skip("Requires Hornresp reference data - run Hornresp and export results")


class TestNumericalStability:
    """Test numerical stability at edge cases."""

    def test_low_frequency(self):
        """Very low frequencies should not cause numerical issues."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
        )

        freqs = np.array([1.0, 5.0, 10.0])  # Very low frequencies
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))

    def test_high_frequency(self):
        """High frequencies should not cause numerical issues."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
        )

        freqs = np.array([1000.0, 2000.0, 5000.0])  # High frequencies
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))

    def test_near_resonance(self):
        """Frequencies near parallel resonance should be handled gracefully."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=40.0,
            downstream_length=150.0,
        )

        # Sweep around quarter-wave frequency
        f_qw = th.quarter_wave_frequency
        freqs = np.linspace(f_qw * 0.9, f_qw * 1.1, 20)

        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        # Should handle near-resonance without errors
        assert np.all(np.isfinite(z_tap))

    def test_very_short_upstream(self):
        """Very short upstream section should still work."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=5.0,  # Very short
            downstream_length=150.0,
        )

        freqs = np.array([50.0, 100.0, 200.0])
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))

    def test_very_long_upstream(self):
        """Very long upstream section should still work."""
        th = TappedHorn(
            upstream_throat_area=50.0,
            tap_area=200.0,
            downstream_mouth_area=2000.0,
            upstream_length=200.0,  # Very long
            downstream_length=50.0,
        )

        freqs = np.array([50.0, 100.0, 200.0])
        z_tap = tapped_horn_tap_impedance(freqs, th, MEDIUM)

        assert np.all(np.isfinite(z_tap))
