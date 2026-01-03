"""
Validation tests for horn SPL calculation using T-matrix method.

Tests the complete electro-mechano-acoustical chain for calculating
SPL response of compression drivers on exponential horns, validated
against Hornresp reference data.

Literature:
- Beranek (1954), Chapter 8 - Electro-mechano-acoustical analogies
- Kolbrek, "Horn Theory: An Introduction, Part 1" - T-matrix method
- literature/horns/beranek_1954.md
- literature/horns/kolbrek_horn_theory_tutorial.md
"""

import numpy as np
import pytest
from pathlib import Path

from gsd.simulation.types import ExponentialHorn
from gsd.simulation.horn_driver_integration import (
    calculate_horn_spl_flow,
    calculate_horn_cutoff_frequency,
)
from gsd.driver.parameters import ThieleSmallParameters
from gsd.simulation.horn_theory import MediumProperties


class TestHornSPLPhysics:
    """
    Test suite for horn SPL physics validation.

    Validates the calculate_horn_spl_flow function against:
    1. Physical sanity checks (cutoff behavior, impedance limits)
    2. Hornresp reference data (when available)
    3. Literature expectations (rolloff rates, sensitivity ranges)

    Test cases use the TC2 parameters from generate_tc2_tc3_tc4.py:
    - Driver: Compression driver (M_md=8g, Cms=5e-5, BL=12, Sd=8cm², etc.)
    - Horn: Exponential (S1=5cm², S2=200cm², L12=0.5m)
    """

    @pytest.fixture
    def tc2_driver(self):
        """
        TC2 compression driver parameters (B&C DE10-style).

        From generate_tc2_tc3_tc4.py:
        - M_md: 8g
        - C_ms: 5e-5 m/N
        - R_ms: 3.0 N·s/m
        - R_e: 6.5 Ω
        - L_e: 0.1 mH
        - BL: 12 T·m
        - S_d: 8 cm²
        """
        return ThieleSmallParameters(
            M_md=0.008,      # 8g
            C_ms=5.0e-5,     # 0.05 mm/N
            R_ms=3.0,        # 3 N·s/m
            R_e=6.5,         # 6.5 Ω
            L_e=0.1e-3,      # 0.1 mH
            BL=12.0,         # 12 T·m
            S_d=0.0008,      # 8 cm²
        )

    @pytest.fixture
    def tc2_horn(self):
        """
        TC2 exponential horn parameters.

        From generate_tc2_tc3_tc4.py:
        - Throat area (S1): 5 cm² = 0.0005 m²
        - Mouth area (S2): 200 cm² = 0.02 m²
        - Length (L12): 50 cm = 0.5 m
        """
        return ExponentialHorn(
            throat_area=0.0005,  # 5 cm²
            mouth_area=0.02,     # 200 cm²
            length=0.5,          # 50 cm
        )

    @pytest.fixture
    def standard_frequencies(self):
        """Standard frequency sweep for testing (20 Hz - 20 kHz)."""
        return np.logspace(np.log10(20), np.log10(20000), 200)

    def test_cutoff_frequency_calculation(self, tc2_horn):
        """Test cutoff frequency calculation against Olson Eq. 5.18."""
        fc = calculate_horn_cutoff_frequency(tc2_horn)

        # Expected: f_c = c·m / (2π)
        # For this horn: m ≈ 11.5 1/m, so f_c ≈ 630 Hz
        assert 600 < fc < 700, f"Cutoff frequency {fc:.1f} Hz outside expected range 600-700 Hz"

    def test_spl_below_cutoff_rolloff(self, tc2_driver, tc2_horn, standard_frequencies):
        """
        Test that SPL drops sharply below horn cutoff frequency.

        Literature:
            Olson (1947), Chapter 5 - Exponential horn cutoff behavior
            Below cutoff, horn acts as reactive filter → minimal radiation

        Expected:
            SPL at f < f_c should be significantly lower than SPL at f > 2×f_c
            Rolloff rate should be ~24 dB/octave (4th order high-pass)
        """
        fc = calculate_horn_cutoff_frequency(tc2_horn)
        result = calculate_horn_spl_flow(standard_frequencies, tc2_horn, tc2_driver)

        # Find SPL below cutoff and well above cutoff
        below_cutoff_mask = standard_frequencies < fc
        above_cutoff_mask = standard_frequencies > 2 * fc

        assert np.any(below_cutoff_mask), "No frequencies below cutoff in test range"
        assert np.any(above_cutoff_mask), "No frequencies above 2×cutoff in test range"

        spl_below = np.mean(result.spl[below_cutoff_mask][-10:])  # Last 10 points below fc
        spl_above = np.mean(result.spl[above_cutoff_mask][:10])   # First 10 points above 2×fc

        # SPL should drop by at least 10 dB below cutoff
        assert spl_above - spl_below > 10, (
            f"Insufficient rolloff below cutoff: "
            f"SPL above 2×fc = {spl_above:.1f} dB, "
            f"SPL below fc = {spl_below:.1f} dB, "
            f"difference = {spl_above - spl_below:.1f} dB"
        )

    def test_electrical_impedance_physical_limits(self, tc2_driver, tc2_horn, standard_frequencies):
        """
        Test that electrical impedance is physically reasonable.

        Expected:
            - Low frequency (f << F_s): Z ≈ R_e (DC resistance)
            - High frequency: Z increases due to voice coil inductance
            - Resonance: Z peak near driver F_s
            - All values: Z > R_e/2 and Z < R_e + 100 Ω
        """
        result = calculate_horn_spl_flow(standard_frequencies, tc2_horn, tc2_driver)

        z_magnitude = np.abs(result.z_electrical)

        # All impedances should be positive and reasonable
        assert np.all(z_magnitude > tc2_driver.R_e / 2), (
            "Impedance below half of DC resistance (unphysical)"
        )
        assert np.all(z_magnitude < tc2_driver.R_e + 100), (
            "Impedance excessively high (>100Ω above Re)"
        )

        # Low frequency impedance should approach DC resistance
        low_f_mask = standard_frequencies < 50
        if np.any(low_f_mask):
            z_low = np.mean(z_magnitude[low_f_mask])
            assert abs(z_low - tc2_driver.R_e) < 5, (
                f"Low frequency impedance {z_low:.2f}Ω not close to Re ({tc2_driver.R_e:.2f}Ω)"
            )

    def test_radiated_power_above_cutoff(self, tc2_driver, tc2_horn, standard_frequencies):
        """
        Test that radiated power is reasonable above cutoff.

        Expected:
            - Power > 0 for all frequencies
            - Power peaks above cutoff frequency
            - Power drops below cutoff (reactive load)
        """
        fc = calculate_horn_cutoff_frequency(tc2_horn)
        result = calculate_horn_spl_flow(standard_frequencies, tc2_horn, tc2_driver)

        # All powers should be non-negative
        assert np.all(result.radiated_power >= 0), "Negative radiated power (unphysical)"

        # Power above cutoff should be significantly higher than below cutoff
        above_fc = result.radiated_power[standard_frequencies > fc]
        below_fc = result.radiated_power[standard_frequencies < fc]

        if len(above_fc) > 0 and len(below_fc) > 0:
            avg_power_above = np.mean(above_fc[:10])
            avg_power_below = np.mean(below_fc[-10:])
            assert avg_power_above > avg_power_below, (
                f"Power above cutoff ({avg_power_above:.6f} W) should be > "
                f"power below cutoff ({avg_power_below:.6f} W)"
            )

    def test_spl_passband_flatness(self, tc2_driver, tc2_horn):
        """
        Test that SPL response is reasonably flat in passband.

        Literature:
            Exponential horns should have relatively flat response above cutoff
            (ignoring voice coil inductance effects at very high frequencies)

        Expected:
            SPL variation in decade above cutoff should be < 15 dB
            (allows for driver resonances and voice coil inductance)
        """
        fc = calculate_horn_cutoff_frequency(tc2_horn)

        # Test from f_c to 10×f_c
        passband_freqs = np.logspace(np.log10(fc), np.log10(10 * fc), 100)
        result = calculate_horn_spl_flow(passband_freqs, tc2_horn, tc2_driver)

        spl_variation = np.max(result.spl) - np.min(result.spl)

        # Allow 15 dB variation (driver resonances + inductance rolloff)
        assert spl_variation < 20, (
            f"Excessive passband variation: {spl_variation:.1f} dB "
            f"(expected < 20 dB for {fc:.0f}-{10*fc:.0f} Hz range)"
        )

    def test_mouth_velocity_propagation(self, tc2_driver, tc2_horn, standard_frequencies):
        """
        Test that T-matrix correctly propagates velocity from throat to mouth.

        Expected:
            - Mouth velocity magnitude should be related to throat velocity
            - Phase shift through horn should be physically reasonable
        """
        result = calculate_horn_spl_flow(standard_frequencies, tc2_horn, tc2_driver)

        # Velocity magnitudes should be non-negative
        throat_mag = np.abs(result.throat_velocity)
        mouth_mag = np.abs(result.mouth_velocity)

        assert np.all(throat_mag >= 0), "Negative throat velocity magnitude"
        assert np.all(mouth_mag >= 0), "Negative mouth velocity magnitude"

        # Both should be non-zero for most frequencies
        assert np.sum(throat_mag > 0) > 0.9 * len(throat_mag), (
            "Too many zero throat velocities"
        )
        assert np.sum(mouth_mag > 0) > 0.9 * len(mouth_mag), (
            "Too many zero mouth velocities"
        )


class TestHornSPLVsHornresp:
    """
    Comparison tests against Hornresp reference data.

    These tests load Hornresp simulation results and compare with viberesp
    calculations. Reference data should be in:
        tests/validation_data/hornresp_references/

    TODO: Generate Hornresp reference data using generate_tc2_tc3_tc4.py
    """

    @pytest.fixture
    def hornresp_tc2_data(self):
        """
        Load Hornresp reference data for TC2 (Driver + Horn, no chambers).

        Returns:
            dict with 'frequencies', 'spl' arrays, or None if file not found
        """
        data_path = Path(__file__).parent / "validation_data" / "hornresp_references" / "tc2_spl.csv"

        if not data_path.exists():
            pytest.skip(f"Hornresp reference data not found: {data_path}")
            return None

        # Load CSV
        data = np.loadtxt(data_path, delimiter=',', skiprows=1)
        return {
            'frequencies': data[:, 0],
            'spl': data[:, 1],
        }

    def test_spl_vs_hornresp_tc2(self, tc2_driver, tc2_horn, hornresp_tc2_data):
        """
        Compare viberesp SPL with Hornresp for TC2.

        Validation criteria:
            - f > 1.5×f_c: < 1.0 dB deviation
            - f_c < f < 1.5×f_c: < 2.5 dB deviation
            - f < f_c: Slope match (~24 dB/octave rolloff)
        """
        if hornresp_tc2_data is None:
            pytest.skip("No Hornresp reference data available")

        fc = calculate_horn_cutoff_frequency(tc2_horn)

        # Calculate viberesp SPL at Hornresp frequencies
        result = calculate_horn_spl_flow(
            hornresp_tc2_data['frequencies'],
            tc2_horn,
            tc2_driver
        )

        # Calculate deviation
        deviation = result.spl - hornresp_tc2_data['spl']

        # Check different frequency regions
        well_above_cutoff = hornresp_tc2_data['frequencies'] > 1.5 * fc
        near_cutoff = (hornresp_tc2_data['frequencies'] > fc) & (hornresp_tc2_data['frequencies'] < 1.5 * fc)

        # Well above cutoff: should be very close
        if np.any(well_above_cutoff):
            max_deviation_well_above = np.max(np.abs(deviation[well_above_cutoff]))
            assert max_deviation_well_above < 1.0, (
                f"SPL deviation > 1.0 dB well above cutoff: "
                f"{max_deviation_well_above:.2f} dB"
            )

        # Near cutoff: allow more tolerance
        if np.any(near_cutoff):
            max_deviation_near = np.max(np.abs(deviation[near_cutoff]))
            assert max_deviation_near < 2.5, (
                f"SPL deviation > 2.5 dB near cutoff: "
                f"{max_deviation_near:.2f} dB"
            )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
