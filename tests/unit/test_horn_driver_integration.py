"""
Unit tests for horn driver integration module.

Tests throat chamber, rear chamber, and complete horn system models.

Literature:
- Olson (1947), Chapter 8 - Horn driver systems
- Beranek (1954), Chapter 5 - Acoustic compliance
- literature/horns/olson_1947.md
- literature/horns/beranek_1954.md
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose
import math

from gsd.simulation import (
    ExponentialHorn,
    MediumProperties,
)
from gsd.simulation.horn_driver_integration import (
    throat_chamber_impedance,
    rear_chamber_impedance,
    horn_system_acoustic_impedance,
    horn_electrical_impedance,
)
from gsd.driver.parameters import ThieleSmallParameters


class TestThroatChamberImpedance:
    """Test throat chamber acoustic impedance model."""

    def test_throat_chamber_compliance(self):
        """Test throat chamber behaves as acoustic compliance."""
        # Compliance impedance: Z = -j/(ω·C)
        # At low frequency: high impedance (stiff spring)
        # At high frequency: low impedance
        freqs = np.array([100.0, 500.0, 1000.0])
        V_tc = 0.001  # 1 liter
        A_tc = 0.005  # 50 cm²

        z_tc = throat_chamber_impedance(freqs, V_tc, A_tc)

        # Check that impedance is purely imaginary (reactance)
        assert_allclose(z_tc.real, 0.0, atol=1e-10)

        # Check that impedance magnitude decreases with frequency
        # (compliance impedance: |Z| = 1/(ω·C))
        assert abs(z_tc[0]) > abs(z_tc[1])
        assert abs(z_tc[1]) > abs(z_tc[2])

        # Check phase is -90° (capacitive reactance)
        for z in z_tc:
            phase = math.degrees(math.atan2(z.imag, z.real))
            assert_allclose(phase, -90.0, atol=1)

    def test_throat_chamber_volume_validation(self):
        """Test that volume must be positive."""
        freqs = np.array([100.0])
        A_tc = 0.005

        with pytest.raises(ValueError, match="V_tc must be > 0"):
            throat_chamber_impedance(freqs, 0.0, A_tc)

        with pytest.raises(ValueError, match="V_tc must be > 0"):
            throat_chamber_impedance(freqs, -0.001, A_tc)

    def test_throat_chamber_area_validation(self):
        """Test that area must be positive."""
        freqs = np.array([100.0])
        V_tc = 0.001

        with pytest.raises(ValueError, match="A_tc must be > 0"):
            throat_chamber_impedance(freqs, V_tc, 0.0)

        with pytest.raises(ValueError, match="A_tc must be > 0"):
            throat_chamber_impedance(freqs, V_tc, -0.005)

    def test_throat_chamber_impedance_magnitude(self):
        """Test throat chamber impedance magnitude calculation."""
        # Using Beranek (1954) theory: C = V/(ρ·c²)
        # Z = 1/(jω·C) = -j·ρ·c²/(ω·V)
        freq = 500.0
        V_tc = 0.001  # m³
        A_tc = 0.005  # m²
        medium = MediumProperties()  # ρ=1.205, c=344

        z_tc = throat_chamber_impedance(
            np.array([freq]), V_tc, A_tc, medium
        )[0]

        # Calculate expected impedance
        omega = 2 * math.pi * freq
        C_tc = V_tc / (medium.rho * medium.c ** 2)
        Z_expected = complex(0, -1 / (omega * C_tc))

        assert_allclose(z_tc, Z_expected, rtol=1e-6)


class TestRearChamberImpedance:
    """Test rear chamber (sealed box) acoustic impedance model."""

    def test_rear_chamber_compliance(self):
        """Test rear chamber behaves as acoustic compliance."""
        # Similar to throat chamber: compliance impedance
        freqs = np.array([100.0, 500.0, 1000.0])
        V_rc = 0.010  # 10 liters
        S_d = 0.022   # 220 cm² (8" driver)

        z_rc = rear_chamber_impedance(freqs, V_rc, S_d)

        # Check that impedance is purely imaginary (reactance)
        assert_allclose(z_rc.real, 0.0, atol=1e-10)

        # Check that impedance magnitude decreases with frequency
        assert abs(z_rc[0]) > abs(z_rc[1])
        assert abs(z_rc[1]) > abs(z_rc[2])

    def test_rear_chamber_volume_validation(self):
        """Test that volume must be positive."""
        freqs = np.array([100.0])
        S_d = 0.022

        with pytest.raises(ValueError, match="V_rc must be > 0"):
            rear_chamber_impedance(freqs, 0.0, S_d)

    def test_rear_chamber_area_validation(self):
        """Test that diaphragm area must be positive."""
        freqs = np.array([100.0])
        V_rc = 0.010

        with pytest.raises(ValueError, match="S_d must be > 0"):
            rear_chamber_impedance(freqs, V_rc, 0.0)


class TestHornSystemAcousticImpedance:
    """Test complete horn system acoustic impedance."""

    def test_horn_only_no_chambers(self):
        """Test horn system with no chambers (Vtc=0, Vrc=0)."""
        horn = ExponentialHorn(
            throat_area=0.005,  # 50 cm²
            mouth_area=0.05,    # 500 cm²
            length=0.3          # 30 cm
        )
        freqs = np.array([100.0, 500.0, 1000.0])

        Z_front, Z_rear = horn_system_acoustic_impedance(
            freqs, horn, V_tc=0.0, V_rc=0.0
        )

        # Front impedance should equal horn throat impedance (no chamber)
        assert len(Z_front) == len(freqs)

        # Rear impedance should be zero (no rear chamber)
        assert_allclose(Z_rear, 0.0, atol=1e-10)

    def test_horn_with_throat_chamber(self):
        """Test horn system with throat chamber."""
        horn = ExponentialHorn(0.005, 0.05, 0.3)
        freqs = np.array([500.0])
        V_tc = 0.001  # 1 liter throat chamber

        Z_front_no_tc, _ = horn_system_acoustic_impedance(
            freqs, horn, V_tc=0.0
        )

        Z_front_with_tc, _ = horn_system_acoustic_impedance(
            freqs, horn, V_tc=V_tc
        )

        # With throat chamber, impedance should be different
        # Throat chamber adds series compliance
        assert not np.allclose(Z_front_with_tc, Z_front_no_tc)

    def test_horn_with_rear_chamber(self):
        """Test horn system with rear chamber."""
        horn = ExponentialHorn(0.005, 0.05, 0.3)
        freqs = np.array([500.0])
        V_rc = 0.010  # 10 liters rear chamber
        S_d = 0.022   # 220 cm²

        _, Z_rear = horn_system_acoustic_impedance(
            freqs, horn, V_rc=V_rc, S_d=S_d
        )

        # Rear impedance should be non-zero (compliance)
        assert not np.allclose(Z_rear, 0.0)

        # Should be purely reactive (compliance)
        assert_allclose(Z_rear[0].real, 0.0, atol=1e-10)

    def test_rear_chamber_requires_diaphragm_area(self):
        """Test that rear chamber requires diaphragm area."""
        horn = ExponentialHorn(0.005, 0.05, 0.3)
        freqs = np.array([500.0])

        with pytest.raises(ValueError, match="S_d must be provided"):
            horn_system_acoustic_impedance(freqs, horn, V_rc=0.010, S_d=None)


class TestHornElectricalImpedance:
    """Test horn-loaded driver electrical impedance model."""

    def setup_method(self):
        """Set up test driver and horn."""
        # Simple test driver (similar to BC 8NDL51)
        self.driver = ThieleSmallParameters(
            M_md=0.026,    # 26g driver mass
            C_ms=1.5e-4,   # Compliance
            R_ms=2.44,     # Mechanical resistance
            R_e=2.6,       # DC resistance
            L_e=0.15e-3,   # Inductance
            BL=7.3,        # Force factor
            S_d=0.022,     # 220 cm²
        )

        self.horn = ExponentialHorn(
            throat_area=0.001,  # 10 cm² (smaller than driver)
            mouth_area=0.01,    # 100 cm²
            length=0.3          # 30 cm
        )

    def test_electrical_impedance_basic(self):
        """Test basic electrical impedance calculation."""
        freq = 500.0
        result = horn_electrical_impedance(
            freq, self.driver, self.horn
        )

        # Check return value structure
        assert 'frequency' in result
        assert 'Ze_magnitude' in result
        assert 'Ze_phase' in result
        assert 'Ze_real' in result
        assert 'Ze_imag' in result
        assert 'diaphragm_velocity' in result
        assert 'diaphragm_displacement' in result

        # Check basic sanity
        assert result['frequency'] == freq
        assert result['Ze_magnitude'] > 0
        assert result['Ze_magnitude'] >= self.driver.R_e  # Ze >= Re
        assert -180 <= result['Ze_phase'] <= 90

    def test_electrical_impedance_frequency_dependence(self):
        """Test that electrical impedance varies with frequency."""
        freqs = [100.0, 500.0, 1000.0, 2000.0]
        impedances = []

        for freq in freqs:
            result = horn_electrical_impedance(
                freq, self.driver, self.horn
            )
            impedances.append(result['Ze_magnitude'])

        # Impedance should vary with frequency
        # (not all values the same)
        assert len(set(impedances)) > 1

    def test_electrical_impedance_with_throat_chamber(self):
        """Test electrical impedance with throat chamber."""
        freq = 500.0

        result_no_tc = horn_electrical_impedance(
            freq, self.driver, self.horn, V_tc=0.0
        )

        result_with_tc = horn_electrical_impedance(
            freq, self.driver, self.horn, V_tc=0.001
        )

        # Throat chamber should affect electrical impedance
        # (changes acoustic load, which reflects to electrical domain)
        # Note: Effect may be small for some systems, but should be non-zero
        assert result_no_tc['Ze_magnitude'] != result_with_tc['Ze_magnitude'], \
            "Throat chamber should affect electrical impedance"

    def test_electrical_impedance_with_rear_chamber(self):
        """Test electrical impedance with rear chamber."""
        freq = 500.0

        result_no_rc = horn_electrical_impedance(
            freq, self.driver, self.horn, V_rc=0.0
        )

        result_with_rc = horn_electrical_impedance(
            freq, self.driver, self.horn, V_rc=0.010
        )

        # Rear chamber should affect electrical impedance
        # Note: Effect may be small for some systems, but should be non-zero
        assert result_no_rc['Ze_magnitude'] != result_with_rc['Ze_magnitude'], \
            "Rear chamber should affect electrical impedance"

    def test_diaphragm_velocity_phase_relationship(self):
        """Test diaphragm velocity and displacement phase relationship."""
        freq = 500.0
        result = horn_electrical_impedance(
            freq, self.driver, self.horn
        )

        # Displacement lags velocity by 90°
        # X = v / (jω)
        # At any frequency, |X| = |v| / ω
        omega = 2 * math.pi * freq
        expected_displacement = result['diaphragm_velocity'] / omega

        assert_allclose(
            result['diaphragm_displacement'],
            expected_displacement,
            rtol=1e-6
        )

    def test_electrical_impedance_validation(self):
        """Test input validation."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            horn_electrical_impedance(0, self.driver, self.horn)

        with pytest.raises(ValueError, match="Frequency must be > 0"):
            horn_electrical_impedance(-100, self.driver, self.horn)


class TestHornSystemIntegration:
    """Integration tests for complete horn system."""

    def setup_method(self):
        """Set up test driver and horn."""
        self.driver = ThieleSmallParameters(
            M_md=0.026, C_ms=1.5e-4, R_ms=2.44,
            R_e=2.6, L_e=0.15e-3, BL=7.3, S_d=0.022,
        )

        self.horn = ExponentialHorn(
            throat_area=0.001,
            mouth_area=0.01,
            length=0.3
        )

    def test_complete_system_with_chambers(self):
        """Test complete horn system with both chambers."""
        freq = 500.0
        V_tc = 0.001  # Throat chamber
        V_rc = 0.010  # Rear chamber

        result = horn_electrical_impedance(
            freq, self.driver, self.horn,
            V_tc=V_tc, V_rc=V_rc
        )

        # Should calculate successfully
        assert result['Ze_magnitude'] > 0
        assert result['diaphragm_velocity'] > 0

    def test_frequency_response_consistency(self):
        """Test that frequency response is physically consistent."""
        freqs = np.logspace(1, 4, 20)  # 10 Hz to 10 kHz

        impedances = []
        velocities = []

        for freq in freqs:
            result = horn_electrical_impedance(
                freq, self.driver, self.horn
            )
            impedances.append(result['Ze_magnitude'])
            velocities.append(result['diaphragm_velocity'])

        # All values should be positive and finite
        assert all(np.isfinite(impedances))
        assert all(np.isfinite(velocities))
        assert all(z > 0 for z in impedances)
        assert all(v >= 0 for v in velocities)
