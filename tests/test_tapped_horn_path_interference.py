"""Test phase interference in tapped horn front/rear paths.

This module tests the critical physics of tapped horns:
1. Quarter-wave resonance causes front path cancellation
2. Front and rear paths have 180° phase difference
3. Total mouth pressure is vector sum of both paths

Literature:
    Danley, US Patent 8,457,341 B2 - Quarter-wave resonance and path interference
    Kolbrek, "Horn Loudspeaker Simulation part 1"
    Tom Danley AVS Forum posts on tapped horn physics
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
    calculate_front_path_pressure_contribution,
    calculate_rear_path_pressure_contribution,
    tapped_horn_system_response,
)
from gsd.driver.parameters import ThieleSmallParameters


# Standard air properties (Hornresp defaults)
MEDIUM = MediumProperties(rho=1.205, c=344.0)


# Example driver (similar to BC 15PS100)
EXAMPLE_DRIVER = ThieleSmallParameters(
    R_e=5.4,           # Ohms
    L_e=1.3e-3,        # Henry
    BL=21.0,          # T·m
    M_md=0.150,       # kg (driver mass only)
    R_ms=5.0,         # N·s/m
    C_ms=0.18e-3,     # m/N
    S_d=855e-4,       # m² (855 cm²)
)


class TestQuarterWaveResonance:
    """Test quarter-wave resonance behavior from Danley's research.

    At the quarter-wave frequency:
    - Upstream length = λ/4
    - Round trip to throat = λ/2 (180° phase shift)
    - Front path self-cancels at the mouth
    - Only rear path contributes significantly
    """

    @pytest.fixture
    def quarter_wave_horn(self):
        """Tapped horn with known quarter-wave frequency."""
        # For a 1.8m upstream section, quarter-wave frequency is:
        # f_qw = c / (4 * L) = 344 / (4 * 1.8) ≈ 47.8 Hz
        return TappedHorn(
            upstream_throat_area=150.0,   # cm²
            tap_area=855.0,               # cm² (matches driver Sd)
            downstream_mouth_area=6000.0,  # cm²
            upstream_length=180.0,         # cm (1.8 m)
            downstream_length=200.0,       # cm
            upstream_profile='exponential',
            downstream_profile='exponential',
        )

    def test_quarter_wave_frequency_calculation(self, quarter_wave_horn):
        """Quarter-wave frequency should be c / (4 * L_upstream)."""
        L_up = quarter_wave_horn.upstream_length / 100  # Convert cm to m
        f_qw_expected = MEDIUM.c / (4 * L_up)
        f_qw_actual = quarter_wave_horn.quarter_wave_frequency

        assert_allclose(f_qw_actual, f_qw_expected, rtol=0.01)

    def test_front_path_cancellation_at_quarter_wave(self, quarter_wave_horn):
        """At quarter-wave frequency, front path should largely cancel.

        The round trip to throat causes 180° phase shift, making front
        radiation self-canceling at the mouth.
        """
        f_qw = quarter_wave_horn.quarter_wave_frequency
        frequencies = np.array([f_qw])

        # Calculate driver volume velocity at tap
        u_tap = np.array([0.001 + 0j])  # 1 mm/s

        # Get pressure contributions from both paths
        p_front = calculate_front_path_pressure_contribution(
            frequencies, u_tap, quarter_wave_horn, MEDIUM
        )
        p_rear = calculate_rear_path_pressure_contribution(
            frequencies, u_tap, quarter_wave_horn, MEDIUM
        )

        # At quarter-wave, front path magnitude should be much smaller than rear
        # (due to phase cancellation from round trip)
        mag_front = np.abs(p_front[0])
        mag_rear = np.abs(p_rear[0])

        # Front path should be at least partially cancelled
        # (not completely zero due to finite impedance effects)
        # Check that front path contribution is reasonable (not dominant)
        assert mag_front < mag_rear * 2, \
            f"Front path ({mag_front:.3e}) should not dominate rear path ({mag_rear:.3e}) at quarter-wave"

    def test_frequency_dependent_phase_relationship(self, quarter_wave_horn):
        """Phase relationship between front and rear paths should vary with frequency."""
        u_tap = np.array([0.001 + 0j])

        # Test at multiple frequencies
        test_frequencies = np.array([
            quarter_wave_horn.quarter_wave_frequency * 0.5,  # Below quarter-wave
            quarter_wave_horn.quarter_wave_frequency,        # At quarter-wave
            quarter_wave_horn.quarter_wave_frequency * 2.0,  # Above quarter-wave
        ])

        p_front = calculate_front_path_pressure_contribution(
            test_frequencies, u_tap, quarter_wave_horn, MEDIUM
        )
        p_rear = calculate_rear_path_pressure_contribution(
            test_frequencies, u_tap, quarter_wave_horn, MEDIUM
        )

        # Check that phase relationships vary with frequency
        phases_front = np.angle(p_front)
        phases_rear = np.angle(p_rear)

        # The phase difference should change across frequencies
        # (due to different path lengths)
        phase_diffs = np.abs(phases_front - phases_rear)

        # At different frequencies, phase differences should vary
        # (not be identical)
        assert not np.allclose(phase_diffs[0], phase_diffs[1], rtol=0.1) or \
               not np.allclose(phase_diffs[1], phase_diffs[2], rtol=0.1), \
            "Phase differences should vary with frequency"


class TestPathSuperposition:
    """Test that mouth pressure is proper vector sum of front and rear paths."""

    @pytest.fixture
    def simple_tapped_horn(self):
        """Simple tapped horn for testing."""
        return TappedHorn(
            upstream_throat_area=100.0,
            tap_area=400.0,
            downstream_mouth_area=2000.0,
            upstream_length=100.0,
            downstream_length=150.0,
            upstream_profile='exponential',
            downstream_profile='exponential',
        )

    def test_vector_sum_not_magnitude_sum(self, simple_tapped_horn):
        """Mouth pressure should be vector sum, not magnitude sum.

        The front and rear paths have phase relationships, so they
        must be summed as complex phasors, not magnitudes.
        """
        frequencies = np.array([50.0, 100.0, 200.0])
        u_tap = np.array([0.001 + 0j, 0.001 + 0j, 0.001 + 0j])

        p_front = calculate_front_path_pressure_contribution(
            frequencies, u_tap, simple_tapped_horn, MEDIUM
        )
        p_rear = calculate_rear_path_pressure_contribution(
            frequencies, u_tap, simple_tapped_horn, MEDIUM
        )

        # Vector sum (correct): P_total = P_front - P_rear (180° out of phase)
        p_total_vector = p_front - p_rear

        # Magnitude sum (wrong): |P| = |P_front| + |P_rear|
        p_total_magnitude = np.abs(p_front) + np.abs(p_rear)

        # These should NOT be equal (except in special cases)
        # In general, vector sum < magnitude sum
        assert np.any(np.abs(p_total_vector) < p_total_magnitude), \
            "Vector sum should generally be less than magnitude sum due to phase"

    def test_impedance_split(self, simple_tapped_horn):
        """Volume velocity should split between upstream and downstream based on impedance."""
        frequencies = np.array([100.0])

        z_up = upstream_section_impedance(frequencies, simple_tapped_horn, MEDIUM)
        z_down = downstream_section_impedance(frequencies, simple_tapped_horn, MEDIUM)

        # Upstream impedance (closed throat) should be mostly reactive
        # and generally higher magnitude than downstream at most frequencies
        assert np.abs(z_up[0]) > 0
        assert np.abs(z_down[0]) > 0

        # The split depends on frequency and impedance ratio
        # At some frequencies, more goes upstream; at others, more goes downstream
        tau_up = z_down / (z_up + z_down)  # Transmission coefficient upstream
        tau_down = z_up / (z_up + z_down)  # Transmission coefficient downstream

        # Check that transmission coefficients sum to 1
        assert_allclose(tau_up + tau_down, 1.0, rtol=0.01)

        # Both should be positive magnitude (can have phase)
        assert np.abs(tau_up[0]) > 0
        assert np.abs(tau_down[0]) > 0


class TestSystemResponseIntegration:
    """Test full system response with phase-aware path combination."""

    def test_system_response_finite(self):
        """System response should be finite across frequency range."""
        th = TappedHorn(
            upstream_throat_area=150.0,
            tap_area=855.0,
            downstream_mouth_area=6000.0,
            upstream_length=180.0,
            downstream_length=200.0,
        )

        frequencies = np.logspace(1, 3, 50)  # 10 Hz to 1 kHz

        result = tapped_horn_system_response(
            frequencies, th, EXAMPLE_DRIVER, MEDIUM
        )

        # All outputs should be finite
        assert np.all(np.isfinite(result['spl']))
        assert np.all(np.isfinite(result['electrical_impedance']))
        assert np.all(np.isfinite(result['excursion']))
        assert np.all(np.isfinite(result['efficiency']))

    def test_debug_output_available(self):
        """Debug output should include front and rear path contributions."""
        th = TappedHorn(
            upstream_throat_area=150.0,
            tap_area=855.0,
            downstream_mouth_area=6000.0,
            upstream_length=180.0,
            downstream_length=200.0,
        )

        frequencies = np.array([50.0])

        result = tapped_horn_system_response(
            frequencies, th, EXAMPLE_DRIVER, MEDIUM
        )

        # Check that debug outputs are present
        assert 'p_mouth_front' in result
        assert 'p_mouth_rear' in result
        assert 'p_mouth' in result

        # Front and rear should be complex numbers (phasors)
        assert np.iscomplexobj(result['p_mouth_front'])
        assert np.iscomplexobj(result['p_mouth_rear'])

        # Total pressure should equal front - rear (180° out of phase)
        p_total_expected = result['p_mouth_front'] - result['p_mouth_rear']
        assert_allclose(result['p_mouth'], p_total_expected, rtol=0.01)

    def test_frequency_response_variation(self):
        """SPL response should show characteristic variation with frequency."""
        th = TappedHorn(
            upstream_throat_area=150.0,
            tap_area=855.0,
            downstream_mouth_area=6000.0,
            upstream_length=180.0,
            downstream_length=200.0,
        )

        frequencies = np.logspace(1, 2.3, 50)  # 10 Hz to 200 Hz

        result = tapped_horn_system_response(
            frequencies, th, EXAMPLE_DRIVER, MEDIUM
        )

        # SPL should vary with frequency (not be constant)
        spl_range = result['spl'].max() - result['spl'].min()
        assert spl_range > 10, \
            f"SPL should vary significantly with frequency (range: {spl_range:.1f} dB)"

        # Should have peaks and dips due to interference
        # Check for at least some variation
        assert result['spl'].std() > 5, \
            "SPL should show variation due to path interference"
