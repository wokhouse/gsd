"""
Unit tests for direct radiator response calculations.

Tests the direct_radiator_electrical_impedance() function for correct
calculation of electrical impedance and SPL.
"""

import math
import pytest

from gsd.driver.response import direct_radiator_electrical_impedance
from gsd.driver import load_driver:
        """Get BC 8NDL51 driver parameters."""
        return load_driver("BC_8NDL51")

    def test_response_returns_all_keys(self, bc_8ndl51_driver):
        """Test that response dictionary contains all expected keys."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)

        expected_keys = {
            'frequency', 'Ze_magnitude', 'Ze_phase', 'Ze_real', 'Ze_imag',
            'SPL', 'diaphragm_velocity', 'diaphragm_velocity_phase',
            'radiation_impedance', 'radiation_resistance', 'radiation_reactance'
        }

        assert set(result.keys()) == expected_keys

    def test_frequency_value_correct(self, bc_8ndl51_driver):
        """Test that frequency is stored correctly."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)
        assert result['frequency'] == 100

    def test_impedance_magnitude_positive(self, bc_8ndl51_driver):
        """Test that impedance magnitude is always positive."""
        for freq in [10, 20, 50, 100, 200, 500, 1000]:
            result = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver)
            assert result['Ze_magnitude'] > 0

    def test_impedance_phase_in_valid_range(self, bc_8ndl51_driver):
        """Test that impedance phase is in valid range (-180 to 180 degrees)."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)
        assert -180 <= result['Ze_phase'] <= 180

    def test_spl_finite(self, bc_8ndl51_driver):
        """Test that SPL is finite (not inf or nan)."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)
        assert math.isfinite(result['SPL'])

    def test_diaphragm_velocity_positive(self, bc_8ndl51_driver):
        """Test that diaphragm velocity magnitude is positive."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)
        assert result['diaphragm_velocity'] >= 0

    def test_radiation_impedance_complex(self, bc_8ndl51_driver):
        """Test that radiation impedance is complex."""
        result = direct_radiator_electrical_impedance(100, bc_8ndl51_driver)
        Z_rad = result['radiation_impedance']

        # Should be a complex number
        assert isinstance(Z_rad, complex)
        # Both resistance and reactance should be accessible
        assert 'radiation_resistance' in result
        assert 'radiation_reactance' in result

    def test_impedance_at_dc(self, bc_8ndl51_driver):
        """Test impedance at very low frequency approaches R_e."""
        # At DC, impedance should approach voice coil resistance
        result = direct_radiator_electrical_impedance(0.1, bc_8ndl51_driver)

        # At very low frequency, Z ≈ R_e (slightly higher due to compliance)
        assert result['Ze_magnitude'] >= bc_8ndl51_driver.R_e * 0.99
        assert result['Ze_magnitude'] <= bc_8ndl51_driver.R_e * 1.5

    def test_impedance_at_resonance(self, bc_8ndl51_driver):
        """Test that impedance calculation works at resonance frequency."""
        fs = bc_8ndl51_driver.F_s

        # Calculate impedance at resonance - should not raise errors
        result = direct_radiator_electrical_impedance(fs, bc_8ndl51_driver)

        # Verify basic properties
        assert result['Ze_magnitude'] > 0
        assert result['frequency'] == fs
        assert math.isfinite(result['Ze_magnitude'])

        # Note: The exact impedance curve shape with acoustic loading is complex
        # and will be validated against Hornresp reference data

    def test_impedance_at_high_frequency(self, bc_8ndl51_driver):
        """Test impedance at high frequency."""
        # At high frequency, impedance should approach R_e + jωL_e
        # (reflected impedance becomes negligible)
        freq = 5000
        result = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver)

        # High frequency impedance should be close to voice coil impedance
        omega = 2 * math.pi * freq
        z_voice_coil = math.sqrt(bc_8ndl51_driver.R_e ** 2 + (omega * bc_8ndl51_driver.L_e) ** 2)

        # Within 20% (allowing for some residual mechanical reflection)
        assert abs(result['Ze_magnitude'] - z_voice_coil) / z_voice_coil < 0.2

    def test_spl_increases_with_frequency(self, bc_8ndl51_driver):
        """Test that SPL generally increases with frequency (flat response expected)."""
        # For a direct radiator in infinite baffle, response should be relatively flat
        # above resonance, with some variation due to radiation impedance

        freqs = [100, 200, 500, 1000, 2000]
        spls = [
            direct_radiator_electrical_impedance(f, bc_8ndl51_driver)['SPL']
            for f in freqs
        ]

        # SPL should not vary by more than 20 dB in this range
        spl_range = max(spls) - min(spls)
        assert spl_range < 20, f"SPL variation too large: {spl_range} dB"

    def test_invalid_frequency_raises_error(self, bc_8ndl51_driver):
        """Test that invalid frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            direct_radiator_electrical_impedance(0, bc_8ndl51_driver)

        with pytest.raises(ValueError, match="Frequency must be > 0"):
            direct_radiator_electrical_impedance(-10, bc_8ndl51_driver)

    def test_invalid_measurement_distance_raises_error(self, bc_8ndl51_driver):
        """Test that invalid measurement distance raises ValueError."""
        with pytest.raises(ValueError, match="Measurement distance must be > 0"):
            direct_radiator_electrical_impedance(100, bc_8ndl51_driver, measurement_distance=0)

        with pytest.raises(ValueError, match="Measurement distance must be > 0"):
            direct_radiator_electrical_impedance(100, bc_8ndl51_driver, measurement_distance=-1)

    def test_spl_decreases_with_distance(self, bc_8ndl51_driver):
        """Test that SPL decreases with measurement distance."""
        freq = 100

        spl_1m = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver, measurement_distance=1.0)['SPL']
        spl_2m = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver, measurement_distance=2.0)['SPL']

        # SPL should decrease by 6 dB when distance doubles (point source in half-space)
        # Allow ±2 dB tolerance for numerical precision
        spl_difference = spl_1m - spl_2m
        assert 4 < spl_difference < 8, f"SPL should decrease by ~6 dB when distance doubles, got {spl_difference} dB"

    def test_different_voltage_affects_spl(self, bc_8ndl51_driver):
        """Test that input voltage affects SPL."""
        freq = 100

        spl_1v = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver, voltage=1.0)['SPL']
        spl_2v = direct_radiator_electrical_impedance(freq, bc_8ndl51_driver, voltage=2.0)['SPL']

        # Double voltage (4x power) should increase SPL by ~6 dB
        # Allow ±1 dB tolerance
        spl_difference = spl_2v - spl_1v
        assert 5 < spl_difference < 7, f"Double voltage should increase SPL by ~6 dB, got {spl_difference} dB"
