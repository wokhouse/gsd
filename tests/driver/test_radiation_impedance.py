"""
Tests for radiation impedance calculations.

Literature:
- Beranek (1954), Chapter 5 - Radiation impedance theory
- Olson (1947), Chapter 5 - Piston radiation
"""

import math
import pytest

from gsd.driver.radiation_impedance import (
    radiation_impedance_piston,
    radiation_impedance_piston_asymptotic_check,
)
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


class TestRadiationImpedancePiston:
    """Test radiation impedance of circular piston in infinite baffle."""

    def test_basic_functionality(self):
        """Test basic radiation impedance calculation."""
        # 12" driver at 100 Hz
        S_d = 0.05  # 500 cm²
        f = 100  # Hz

        Z = radiation_impedance_piston(f, S_d)

        # Should be complex (real + imaginary)
        assert isinstance(Z, complex)

        # Both parts should be positive
        assert Z.real > 0  # Radiation resistance
        assert Z.imag > 0  # Radiation reactance (mass loading)

    def test_low_frequency_regime(self):
        """Test radiation impedance at low frequency (ka << 1)."""
        S_d = 0.05  # 500 cm²
        f = 20  # Hz (low frequency)

        Z = radiation_impedance_piston(f, S_d)

        # At low frequency, reactance >> resistance (mass loading dominates)
        assert Z.imag > Z.real

        # Resistance should be very small (~ka²/2)
        # Reactance should be moderate (~4ka/3π)
        assert Z.real < 0.1  # Very small resistance
        assert Z.imag > 0.5  # Significant mass loading

    def test_high_frequency_regime(self):
        """Test radiation impedance at high frequency (ka >> 1)."""
        S_d = 0.05  # 500 cm²
        f = 5000  # Hz (high frequency)

        Z = radiation_impedance_piston(f, S_d)

        # At high frequency, Z → ρc·S (purely resistive)
        Z0 = AIR_DENSITY * SPEED_OF_SOUND
        Z_expected = Z0 * S_d

        # Magnitude should approach ρc·S
        assert abs(Z - Z_expected) / Z_expected < 0.1  # Within 10%

        # Phase should approach 0 (purely resistive)
        phase = math.degrees(math.atan2(Z.imag, Z.real))
        assert abs(phase) < 20  # Small phase angle

    def test_frequency_scaling(self):
        """Test how radiation impedance changes with frequency."""
        S_d = 0.05  # 500 cm²

        # Low frequency
        Z_low = radiation_impedance_piston(50, S_d)

        # Mid frequency
        Z_mid = radiation_impedance_piston(500, S_d)

        # High frequency
        Z_high = radiation_impedance_piston(5000, S_d)

        # Resistance should increase with frequency (more power radiation)
        assert Z_low.real < Z_mid.real < Z_high.real

        # Magnitude should increase with frequency
        assert abs(Z_low) < abs(Z_mid) < abs(Z_high)

    def test_area_scaling(self):
        """Test how radiation impedance scales with piston area."""
        f = 5000  # Hz (high frequency for linear scaling)

        # Small piston
        Z_small = radiation_impedance_piston(f, 0.01)  # 100 cm²

        # Large piston
        Z_large = radiation_impedance_piston(f, 0.10)  # 1000 cm²

        # At high frequency, impedance should scale roughly linearly with area
        # Z → ρc·S as ka >> 1
        ratio = abs(Z_large) / abs(Z_small)

        # Should be approximately 10x (area ratio)
        assert 8 < ratio < 12  # Allow 20% tolerance

    def test_validation_rejects_zero_frequency(self):
        """Test that zero frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            radiation_impedance_piston(0, 0.05)

    def test_validation_rejects_negative_frequency(self):
        """Test that negative frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be > 0"):
            radiation_impedance_piston(-100, 0.05)

    def test_validation_rejects_zero_area(self):
        """Test that zero piston area raises ValueError."""
        with pytest.raises(ValueError, match="Piston area must be > 0"):
            radiation_impedance_piston(100, 0)

    def test_validation_rejects_negative_area(self):
        """Test that negative piston area raises ValueError."""
        with pytest.raises(ValueError, match="Piston area must be > 0"):
            radiation_impedance_piston(100, -0.05)

    def test_very_low_frequency_asymptote(self):
        """
        Test low-frequency asymptotic behavior.

        Beranek (1954), Eq. 5.20: For ka << 1:
        - R₁ ≈ (ka)² / 2
        - X₁ ≈ 4ka / (3π)
        """
        S_d = 0.01  # 100 cm² (smaller piston for lower ka)
        f = 5  # Hz (very low frequency, ka ~ 0.005)

        result = radiation_impedance_piston_asymptotic_check(f, S_d)

        # Should be in low-frequency regime
        assert result['ka'] < 0.01

        # Full calculation should match asymptote
        # Error should be small (<1% for ka < 0.01)
        assert result['asymptote_error'] < 0.01

        # Check resistance scales as f² (ka²)
        Z1 = radiation_impedance_piston(f, S_d)
        Z2 = radiation_impedance_piston(2 * f, S_d)
        # Resistance should increase by ~4x when frequency doubles
        assert abs(Z2.real / Z1.real - 4.0) < 0.5  # Within 50%

    def test_high_frequency_limit(self):
        """
        Test high-frequency limit behavior.

        Beranek (1954), Eq. 5.20: For ka >> 1:
        - R₁ → 1
        - X₁ → 0
        - Z_R → ρc·S (purely resistive)
        """
        S_d = 0.05  # 500 cm²
        f = 10000  # Hz (high frequency, ka >> 1)

        result = radiation_impedance_piston_asymptotic_check(f, S_d)

        # Should be in high-frequency regime
        assert result['ka'] > 5

        # Full calculation should approach high-frequency limit
        Z_expected = result['high_freq_limit']
        relative_error = abs(result['full'] - Z_expected) / abs(Z_expected)
        assert relative_error < 0.05  # Within 5%

        # Impedance should be nearly purely resistive
        phase = math.degrees(math.atan2(result['full'].imag, result['full'].real))
        assert abs(phase) < 10  # Small phase angle

    def test_continuity_at_transition(self):
        """Test that impedance is continuous across asymptote transition."""
        S_d = 0.05  # 500 cm²

        # Calculate impedance around ka = 0.01 (transition point)
        f1 = 10  # Hz (ka < 0.01)
        f2 = 20  # Hz (ka > 0.01)

        Z1 = radiation_impedance_piston(f1, S_d)
        Z2 = radiation_impedance_piston(f2, S_d)

        # Impedance should be continuous (no sudden jumps)
        # Even though we switch from asymptote to full expression
        relative_change = abs(Z2 - Z1) / abs(Z1)
        assert relative_change < 1.0  # Less than 100% change

    def test_ka_calculation(self):
        """Test that dimensionless frequency parameter ka is correct."""
        S_d = 0.05  # 500 cm²
        f = 100  # Hz

        result = radiation_impedance_piston_asymptotic_check(f, S_d)

        # Calculate ka manually
        k = 2 * math.pi * f / SPEED_OF_SOUND
        a = math.sqrt(S_d / math.pi)
        ka_expected = k * a

        assert abs(result['ka'] - ka_expected) < 1e-6

    def test_characteristic_impedance_scaling(self):
        """Test that impedance scales with ρc."""
        S_d = 0.05  # 500 cm²
        f = 1000  # Hz

        # Standard conditions
        Z1 = radiation_impedance_piston(f, S_d, SPEED_OF_SOUND, AIR_DENSITY)

        # Different air density
        Z2 = radiation_impedance_piston(f, S_d, SPEED_OF_SOUND, 2 * AIR_DENSITY)

        # Impedance should scale linearly with air density
        assert abs(Z2.real / Z1.real - 2.0) < 0.01
        assert abs(Z2.imag / Z1.imag - 2.0) < 0.01

    def test_physical_reasonableness(self):
        """Test that impedance values are physically reasonable."""
        S_d = 0.05  # 500 cm² (typical 12" driver)

        # Test across frequency range
        frequencies = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]

        for f in frequencies:
            Z = radiation_impedance_piston(f, S_d)

            # Resistance should always be positive
            assert Z.real > 0

            # Reactance should always be positive (mass loading)
            assert Z.imag > 0

            # Magnitude should be reasonable (not infinity, not zero)
            assert 0 < abs(Z) < 1000  # Less than 1000 rayl·m²

    def test_beranek_reference_values(self):
        """
        Test against reference values from Beranek (1954).

        Beranek (1954), Chapter 5 provides impedance curves for
        circular pistons. This test checks our calculation against
        expected values at specific ka points.
        """
        S_d = 0.01  # 100 cm²
        f = 1000  # Hz (ka ≈ 1.0 for small piston)

        result = radiation_impedance_piston_asymptotic_check(f, S_d)

        # At ka ≈ 1:
        # - R₁ should be around 0.5-0.7
        # - X₁ should be around 0.5-0.7
        ka = result['ka']
        Z0 = AIR_DENSITY * SPEED_OF_SOUND

        # Normalize by ρc·S
        Z_normalized = result['full'] / (Z0 * S_d)

        # Check that real and imaginary parts are in reasonable range
        assert 0 < Z_normalized.real < 1  # R₁ should be 0-1
        assert 0 < Z_normalized.imag < 1  # X₁ should be 0-1
