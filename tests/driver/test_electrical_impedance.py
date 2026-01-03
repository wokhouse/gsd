"""
Tests for electrical impedance calculations.

Literature:
- COMSOL (2020) - Electro-mechano-acoustical equivalent circuit
- Small (1972) - Electrical impedance model
"""

import math
import pytest

from gsd.driver.electrical_impedance import (
    electrical_impedance_bare_driver,
    electrical_impedance_at_resonance,
    electrical_impedance_high_frequency_limit,
)
from gsd.driver.parameters import ThieleSmallParameters


class TestElectricalImpedanceBareDriver:
    """Test electrical impedance of bare driver."""

    @pytest.fixture
    def sample_driver(self):
        """Create a sample driver for testing."""
        return ThieleSmallParameters(
            M_md=0.054,    # 54g
            C_ms=0.00019,  # Compliance (m/N)
            R_ms=5.2,      # Mechanical resistance (N·s/m)
            R_e=3.1,       # DC resistance (Ω)
            L_e=0.72e-3,   # 0.72 mH
            BL=16.5,       # Force factor (T·m)
            S_d=0.0522     # 522 cm²
        )

    def test_basic_functionality(self, sample_driver):
        """Test basic electrical impedance calculation."""
        f = 100  # Hz
        Z = electrical_impedance_bare_driver(f, sample_driver)

        # Should be complex
        assert isinstance(Z, complex)

        # Resistance should be positive
        assert Z.real > 0

        # Reactance can be positive (inductive) or negative (capacitive)
        # depending on frequency

    def test_impedance_at_dc(self, sample_driver):
        """Test impedance at very low frequency (approaches DC)."""
        f = 1  # Hz (very low frequency)
        Z = electrical_impedance_bare_driver(f, sample_driver)

        # At DC, should approach R_e (voice coil DC resistance)
        # Compliance dominates mechanical impedance (capacitive)
        # But voice coil inductance also contributes (inductive)
        # Net reactance depends on which dominates
        assert Z.real > sample_driver.R_e  # Some reflected resistance

        # Reactance can be positive or negative depending on L_e vs C_ms
        # At 1 Hz, voice coil inductance (jωL_e) typically dominates
        # so reactance is often positive
        assert isinstance(Z.imag, float)  # Just check it's a number

    def test_impedance_at_resonance(self, sample_driver):
        """Test impedance at driver resonance frequency."""
        # Calculate impedance at resonance
        Z_res = electrical_impedance_at_resonance(sample_driver)

        # At resonance, mechanical mass and compliance cancel
        # Reflected impedance is purely resistive: (BL)² / R_ms
        Z_reflected_expected = (sample_driver.BL ** 2) / sample_driver.R_ms
        Z_expected = sample_driver.R_e + Z_reflected_expected

        # Real part should peak near this value
        assert abs(Z_res.real - Z_expected) < 5.0  # Within 5Ω

        # Should have a peak in resistance
        Z_low = electrical_impedance_bare_driver(sample_driver.F_s / 2, sample_driver)
        Z_high = electrical_impedance_bare_driver(sample_driver.F_s * 2, sample_driver)

        assert Z_res.real > Z_low.real
        assert Z_res.real > Z_high.real

    def test_impedance_at_high_frequency(self, sample_driver):
        """Test impedance at high frequency."""
        f = 10000  # Hz (high frequency)
        Z = electrical_impedance_bare_driver(f, sample_driver)

        # At high frequency, mechanical impedance is dominated by mass
        # Reflected impedance becomes small (inductive mass reactance)
        # Total impedance approaches R_e + jωL_e

        # Real part should be close to R_e
        assert abs(Z.real - sample_driver.R_e) < 1.0  # Within 1Ω

        # Imaginary part should be positive (inductive voice coil)
        assert Z.imag > 0

    def test_phase_response(self, sample_driver):
        """Test impedance phase response across frequency range."""
        frequencies = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]

        for f in frequencies:
            Z = electrical_impedance_bare_driver(f, sample_driver)
            phase = math.degrees(math.atan2(Z.imag, Z.real))

            # Phase should be reasonable (-90° to +90°)
            assert -90 < phase < 90

    def test_phase_at_resonance(self, sample_driver):
        """Test phase behavior at and around resonance."""
        # At resonance, impedance should be mostly resistive
        Z_res = electrical_impedance_at_resonance(sample_driver)
        phase_res = math.degrees(math.atan2(Z_res.imag, Z_res.real))

        # Phase at resonance should be close to zero (mostly resistive)
        assert abs(phase_res) < 10  # Within ±10°

        # Check phase changes significantly away from resonance
        Z_below = electrical_impedance_bare_driver(sample_driver.F_s * 0.5, sample_driver)
        Z_above = electrical_impedance_bare_driver(sample_driver.F_s * 2, sample_driver)

        phase_below = math.degrees(math.atan2(Z_below.imag, Z_below.real))
        phase_above = math.degrees(math.atan2(Z_above.imag, Z_above.real))

        # Phase should be different below and above resonance
        # (may be positive or negative depending on L_e vs mechanical reactance)
        assert abs(phase_above - phase_below) > 10  # Significant phase change

    def test_effect_of_acoustic_load(self, sample_driver):
        """Test effect of acoustic load on impedance."""
        f = 100  # Hz

        # Bare driver (no load)
        Z_bare = electrical_impedance_bare_driver(f, sample_driver, acoustic_load=0j)

        # With acoustic load (radiation impedance)
        # Typical radiation impedance for 12" driver at 100 Hz
        Z_load = electrical_impedance_bare_driver(f, sample_driver, acoustic_load=1+5j)

        # Acoustic load should change the impedance
        # (typically increases resistance slightly near resonance)
        assert Z_bare != Z_load

    def test_impedance_magnitude_increases_with_bl(self, sample_driver):
        """Test that higher BL increases impedance at resonance."""
        f = sample_driver.F_s

        # Normal BL
        Z1 = electrical_impedance_bare_driver(f, sample_driver)

        # Double BL (create new driver)
        driver_high_bl = ThieleSmallParameters(
            M_md=sample_driver.M_ms,
            C_ms=sample_driver.C_ms,
            R_ms=sample_driver.R_ms,
            R_e=sample_driver.R_e,
            L_e=sample_driver.L_e,
            BL=sample_driver.BL * 2,  # Double BL
            S_d=sample_driver.S_d
        )
        Z2 = electrical_impedance_bare_driver(f, driver_high_bl)

        # Higher BL should increase impedance at resonance
        assert Z2.real > Z1.real

    def test_validation_rejects_zero_frequency(self, sample_driver):
        """Test that zero frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            electrical_impedance_bare_driver(0, sample_driver)

    def test_validation_rejects_negative_frequency(self, sample_driver):
        """Test that negative frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            electrical_impedance_bare_driver(-100, sample_driver)

    def test_validation_rejects_invalid_driver_type(self):
        """Test that non-ThieleSmallParameters raises TypeError."""
        with pytest.raises(TypeError, match="driver must be ThieleSmallParameters"):
            electrical_impedance_bare_driver(100, "not_a_driver")

    def test_impedance_shape(self, sample_driver):
        """Test that impedance has expected shape (peak at F_s)."""
        frequencies = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 500, 1000]
        impedances = [
            abs(electrical_impedance_bare_driver(f, sample_driver))
            for f in frequencies
        ]

        # Find maximum
        max_impedance = max(impedances)
        max_index = impedances.index(max_impedance)
        freq_at_max = frequencies[max_index]

        # Maximum should be near F_s
        # Allow factor of 2 tolerance
        assert 0.5 < freq_at_max / sample_driver.F_s < 2.0

    def test_minimum_impedance_at_high_frequency(self, sample_driver):
        """Test that impedance minimum approaches R_e at high frequency."""
        # High frequency: reflected impedance is small
        Z_hf = electrical_impedance_high_frequency_limit(sample_driver, 10000)

        # Should be close to voice coil resistance
        assert abs(Z_hf.real - sample_driver.R_e) < 2.0

        # Reactance should be positive (inductive)
        assert Z_hf.imag > 0

    def test_voice_coil_inductance_effect(self, sample_driver):
        """Test effect of voice coil inductance."""
        f = 1000  # Hz (inductance matters at higher frequencies)

        # Normal inductance
        Z1 = electrical_impedance_bare_driver(f, sample_driver)

        # Double inductance
        driver_high_L = ThieleSmallParameters(
            M_md=sample_driver.M_ms,
            C_ms=sample_driver.C_ms,
            R_ms=sample_driver.R_ms,
            R_e=sample_driver.R_e,
            L_e=sample_driver.L_e * 2,  # Double L_e
            BL=sample_driver.BL,
            S_d=sample_driver.S_d
        )
        Z2 = electrical_impedance_bare_driver(f, driver_high_L)

        # Higher inductance should increase reactance
        assert Z2.imag > Z1.imag

    def test_mechanical_resistance_effect(self, sample_driver):
        """Test effect of mechanical resistance on impedance peak."""
        # Low mechanical resistance (high Q)
        driver_low_Rms = ThieleSmallParameters(
            M_md=sample_driver.M_ms,
            C_ms=sample_driver.C_ms,
            R_ms=1.0,  # Low resistance
            R_e=sample_driver.R_e,
            L_e=sample_driver.L_e,
            BL=sample_driver.BL,
            S_d=sample_driver.S_d
        )
        Z_low_Rms = electrical_impedance_at_resonance(driver_low_Rms)

        # High mechanical resistance (low Q)
        driver_high_Rms = ThieleSmallParameters(
            M_md=sample_driver.M_ms,
            C_ms=sample_driver.C_ms,
            R_ms=20.0,  # High resistance
            R_e=sample_driver.R_e,
            L_e=sample_driver.L_e,
            BL=sample_driver.BL,
            S_d=sample_driver.S_d
        )
        Z_high_Rms = electrical_impedance_at_resonance(driver_high_Rms)

        # Lower Rms should give higher impedance peak at resonance
        assert Z_low_Rms.real > Z_high_Rms.real

    def test_comsol_example_driver(self):
        """Test with COMSOL example driver parameters."""
        # COMSOL (2020), Table 2 example driver
        driver = ThieleSmallParameters(
            M_md=0.0334,
            C_ms=0.00118,
            R_ms=1.85,
            R_e=6.4,
            L_e=6.89e-3,
            BL=11.4,
            S_d=0.0452
        )

        # Calculate impedance at resonance
        Z_res = electrical_impedance_at_resonance(driver)

        # Expected impedance at resonance:
        # Z = R_e + (BL)² / R_ms
        #   = 6.4 + (11.4)² / 1.85
        #   = 6.4 + 70.2
        #   = 76.6 Ω
        Z_expected = driver.R_e + (driver.BL ** 2) / driver.R_ms

        assert abs(Z_res.real - Z_expected) < 5.0  # Within 5Ω

    def test_physical_reasonableness(self, sample_driver):
        """Test that impedance values are physically reasonable."""
        frequencies = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]

        for f in frequencies:
            Z = electrical_impedance_bare_driver(f, sample_driver)

            # Resistance should always be positive
            assert Z.real > 0

            # Magnitude should be reasonable (not infinity, not near zero)
            assert 1 < abs(Z) < 1000  # 1Ω to 1kΩ

            # At very high frequency, shouldn't be ridiculously high
            if f > 5000:
                assert abs(Z) < 200  # < 200Ω at 5kHz+
