"""
Unit tests for front-loaded horn enclosure module.

Tests FrontLoadedHorn class and its methods.

Literature:
- Olson (1947), Chapter 8 - Horn driver systems
- Beranek (1954), Chapter 5 - Electromechanical analogies
- literature/horns/olson_1947.md
- literature/horns/beranek_1954.md
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose
import math

from gsd.simulation.types import ExponentialHorn
from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.simulation.horn_theory import MediumProperties


class TestFrontLoadedHorn:
    """Test FrontLoadedHorn enclosure class."""

    def setup_method(self):
        """Set up test driver and horn for all tests."""
        # Simple test driver
        self.driver = ThieleSmallParameters(
            M_md=0.026,    # 26g driver mass
            C_ms=1.5e-4,   # Compliance
            R_ms=2.44,     # Mechanical resistance
            R_e=2.6,       # DC resistance
            L_e=0.15e-3,   # Inductance
            BL=7.3,        # Force factor
            S_d=0.022,     # 220 cm²
        )

        # Exponential horn
        self.horn = ExponentialHorn(
            throat_area=0.001,  # 10 cm²
            mouth_area=0.01,    # 100 cm²
            length=0.3          # 30 cm
        )

    def test_basic_creation(self):
        """Test basic FrontLoadedHorn creation."""
        flh = FrontLoadedHorn(self.driver, self.horn)

        assert flh.driver is self.driver
        assert flh.horn is self.horn
        assert flh.V_tc == 0.0  # No throat chamber by default
        assert flh.V_rc == 0.0  # No rear chamber by default
        assert flh.A_tc == self.horn.throat_area  # Defaults to horn throat

    def test_with_throat_chamber(self):
        """Test FrontLoadedHorn with throat chamber."""
        flh = FrontLoadedHorn(
            self.driver,
            self.horn,
            V_tc=0.001  # 1 liter throat chamber
        )

        assert flh.V_tc == 0.001
        assert flh.A_tc == self.horn.throat_area

    def test_with_rear_chamber(self):
        """Test FrontLoadedHorn with rear chamber."""
        flh = FrontLoadedHorn(
            self.driver,
            self.horn,
            V_rc=0.010  # 10 liters rear chamber
        )

        assert flh.V_rc == 0.010

    def test_with_both_chambers(self):
        """Test FrontLoadedHorn with both chambers."""
        flh = FrontLoadedHorn(
            self.driver,
            self.horn,
            V_tc=0.001,
            V_rc=0.010
        )

        assert flh.V_tc == 0.001
        assert flh.V_rc == 0.010

    def test_custom_throat_chamber_area(self):
        """Test FrontLoadedHorn with custom throat chamber area."""
        flh = FrontLoadedHorn(
            self.driver,
            self.horn,
            V_tc=0.001,
            A_tc=0.002  # Custom area
        )

        assert flh.A_tc == 0.002


class TestElectricalImpedance:
    """Test electrical impedance calculation methods."""

    def setup_method(self):
        """Set up test system."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(0.001, 0.01, 0.3)
        self.flh = FrontLoadedHorn(self.driver, self.horn)

    def test_electrical_impedance_single_frequency(self):
        """Test electrical impedance at single frequency."""
        freq = 500.0
        result = self.flh.electrical_impedance(freq)

        # Check return value structure
        assert 'frequency' in result
        assert 'Ze_magnitude' in result
        assert 'Ze_phase' in result
        assert 'Ze_real' in result
        assert 'Ze_imag' in result
        assert 'diaphragm_velocity' in result
        assert 'diaphragm_displacement' in result
        assert 'Z_front' in result
        assert 'Z_rear' in result

        # Check basic sanity
        assert result['frequency'] == freq
        assert result['Ze_magnitude'] > 0
        assert result['Ze_magnitude'] >= self.driver.R_e

    def test_electrical_impedance_array(self):
        """Test electrical impedance across frequency array."""
        freqs = np.array([100.0, 500.0, 1000.0])
        result = self.flh.electrical_impedance_array(freqs)

        # Check return value structure
        assert 'frequencies' in result
        assert 'Ze_magnitude' in result
        assert 'Ze_phase' in result
        assert 'Ze_real' in result
        assert 'Ze_imag' in result

        # Check array shapes
        assert len(result['frequencies']) == len(freqs)
        assert len(result['Ze_magnitude']) == len(freqs)
        assert len(result['Ze_phase']) == len(freqs)

        # Check all values are positive
        assert all(result['Ze_magnitude'] > 0)

    def test_electrical_impedance_with_voltage(self):
        """Test electrical impedance with different voltage."""
        freq = 500.0
        result_2v = self.flh.electrical_impedance(freq, voltage=2.0)
        result_5v = self.flh.electrical_impedance(freq, voltage=5.0)

        # Impedance should be independent of voltage
        # (linear system)
        assert_allclose(
            result_2v['Ze_magnitude'],
            result_5v['Ze_magnitude'],
            rtol=1e-10
        )

        # Diaphragm velocity should scale with voltage
        assert_allclose(
            result_5v['diaphragm_velocity'] / result_2v['diaphragm_velocity'],
            5.0 / 2.0,
            rtol=1e-6
        )


class TestAcousticPower:
    """Test acoustic power calculation."""

    def setup_method(self):
        """Set up test system."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(0.001, 0.01, 0.3)
        self.flh = FrontLoadedHorn(self.driver, self.horn)

    def test_acoustic_power_single_frequency(self):
        """Test acoustic power calculation."""
        freq = 500.0
        power = self.flh.acoustic_power(freq)

        # Power should be positive and finite
        assert power >= 0
        assert np.isfinite(power)

    def test_acoustic_power_voltage_scaling(self):
        """Test that power scales with voltage²."""
        freq = 500.0
        power_2v = self.flh.acoustic_power(freq, voltage=2.0)
        power_4v = self.flh.acoustic_power(freq, voltage=4.0)

        # Power should scale with V²
        # P_4v / P_2v ≈ (4/2)² = 4
        ratio = power_4v / power_2v if power_2v > 0 else 0
        assert_allclose(ratio, 4.0, rtol=1e-3)


class TestSPLResponse:
    """Test SPL response calculation."""

    def setup_method(self):
        """Set up test system."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(0.001, 0.01, 0.3)
        self.flh = FrontLoadedHorn(self.driver, self.horn)

    def test_spl_single_frequency(self):
        """Test SPL calculation at single frequency."""
        freq = 500.0
        spl = self.flh.spl_response(freq)

        # SPL should be finite
        assert np.isfinite(spl)

        # SPL at 1m for 2.83V into 8Ω should be reasonable
        # (not extremely low or high)
        assert 40 < spl < 120  # Typical range

    def test_spl_array(self):
        """Test SPL response across frequency array."""
        freqs = np.logspace(1, 4, 10)
        result = self.flh.spl_response_array(freqs)

        # Check return value structure
        assert 'frequencies' in result
        assert 'SPL' in result

        # Check array shapes
        assert len(result['frequencies']) == len(freqs)
        assert len(result['SPL']) == len(freqs)

        # Check all values are finite
        assert all(np.isfinite(result['SPL']))

    def test_spl_distance_scaling(self):
        """Test SPL inverse-distance law."""
        freq = 1000.0
        spl_1m = self.flh.spl_response(freq, measurement_distance=1.0)
        spl_2m = self.flh.spl_response(freq, measurement_distance=2.0)

        # SPL should decrease by 6 dB when distance doubles
        # (half-space radiation)
        diff = spl_1m - spl_2m
        assert_allclose(diff, 6.0, rtol=0.1)  # 10% tolerance


class TestSystemEfficiency:
    """Test system efficiency calculation."""

    def setup_method(self):
        """Set up test system."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(0.001, 0.01, 0.3)
        self.flh = FrontLoadedHorn(self.driver, self.horn)

    def test_system_efficiency_range(self):
        """Test that efficiency is in valid range."""
        freq = 500.0
        efficiency = self.flh.system_efficiency(freq)

        # Efficiency should be 0-1 (0-100%)
        assert 0 <= efficiency <= 1

    def test_system_efficiency_independent_of_voltage(self):
        """Test that efficiency is independent of voltage."""
        freq = 500.0
        eff_2v = self.flh.system_efficiency(freq, voltage=2.0)
        eff_5v = self.flh.system_efficiency(freq, voltage=5.0)

        # Efficiency should be the same (ratio of powers)
        assert_allclose(eff_2v, eff_5v, rtol=1e-6)


class TestCutoffFrequency:
    """Test cutoff frequency calculation."""

    def test_cutoff_frequency_calculation(self):
        """Test cutoff frequency calculation."""
        driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        horn = ExponentialHorn(0.005, 0.05, 0.3)
        flh = FrontLoadedHorn(driver, horn)

        fc = flh.cutoff_frequency()

        # Check cutoff frequency is positive and reasonable
        assert fc > 0

        # Kolbrek convention: f_c = c·m_olson/(4π) where m_olson = ln(S₂/S₁)/L
        # This matches Hornresp's F12 parameter
        # Verify against direct calculation
        medium = MediumProperties()
        m_olson = np.log(horn.mouth_area / horn.throat_area) / horn.length
        expected_fc = (medium.c * m_olson) / (4 * math.pi)
        assert_allclose(fc, expected_fc, rtol=1e-6)


class TestSystemParameters:
    """Test horn system parameters."""

    def test_system_parameters(self):
        """Test system parameter calculation."""
        driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        horn = ExponentialHorn(0.005, 0.05, 0.3)
        flh = FrontLoadedHorn(driver, horn)

        params = flh.horn_system_parameters()

        # Check all expected keys are present
        expected_keys = [
            'cutoff_frequency',
            'flare_constant',
            'expansion_ratio',
            'horn_length',
            'throat_radius',
            'mouth_radius',
            'has_throat_chamber',
            'has_rear_chamber',
            'driver_resonance',
            'throat_chamber_volume',
            'rear_chamber_volume',
        ]

        for key in expected_keys:
            assert key in params

        # Check values
        assert params['cutoff_frequency'] > 0
        assert params['flare_constant'] > 0
        assert params['expansion_ratio'] == 10.0
        assert params['horn_length'] == 0.3
        assert not params['has_throat_chamber']
        assert not params['has_rear_chamber']
        assert params['driver_resonance'] == driver.F_s


class TestFrontLoadedHornIntegration:
    """Integration tests for complete front-loaded horn system."""

    def setup_method(self):
        """Set up test system."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(0.001, 0.01, 0.3)

    def test_complete_system_with_chambers(self):
        """Test complete system with both chambers."""
        flh = FrontLoadedHorn(
            self.driver,
            self.horn,
            V_tc=0.001,
            V_rc=0.010
        )

        # Should calculate all outputs successfully
        freq = 500.0

        ze_result = flh.electrical_impedance(freq)
        assert ze_result['Ze_magnitude'] > 0

        power = flh.acoustic_power(freq)
        assert power >= 0

        spl = flh.spl_response(freq)
        assert np.isfinite(spl)

        efficiency = flh.system_efficiency(freq)
        assert 0 <= efficiency <= 1

    def test_frequency_response_consistency(self):
        """Test that frequency response is physically consistent."""
        flh = FrontLoadedHorn(self.driver, self.horn)
        freqs = np.logspace(1, 4, 20)

        # Calculate frequency response
        result = flh.electrical_impedance_array(freqs)
        spl_result = flh.spl_response_array(freqs)

        # All values should be finite and positive
        assert all(np.isfinite(result['Ze_magnitude']))
        assert all(result['Ze_magnitude'] > 0)
        assert all(np.isfinite(spl_result['SPL']))

    def test_horn_loading_effect(self):
        """Test that horn loading affects response."""
        # System with no horn (just driver in infinite baffle)
        # would have very different response than horn-loaded system

        # Compare horn with different flare constants
        horn1 = ExponentialHorn(0.001, 0.01, 0.3)  # Moderate flare
        horn2 = ExponentialHorn(0.001, 0.01, 0.6)  # Longer horn, less flare

        flh1 = FrontLoadedHorn(self.driver, horn1)
        flh2 = FrontLoadedHorn(self.driver, horn2)

        freq = 500.0
        ze1 = flh1.electrical_impedance(freq)['Ze_magnitude']
        ze2 = flh2.electrical_impedance(freq)['Ze_magnitude']

        # Different horn geometries should give different impedances
        # (not exactly equal - even small differences count)
        assert ze1 != ze2, "Different horn geometries should produce different impedances"
