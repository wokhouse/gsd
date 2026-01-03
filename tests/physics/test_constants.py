"""
Tests for physical constants and helper functions.

Literature:
- Kinsler et al. (1982), Chapter 1 - Standard conditions
- Beranek (1954), Chapter 1 - Air properties
"""

import numpy as np
import pytest

from gsd.simulation.constants import (
    AIR_DENSITY,
    ATMOSPHERIC_PRESSURE,
    CHARACTERISTIC_IMPEDANCE_AIR,
    PI,
    SPEED_OF_SOUND,
    angular_frequency,
    wavelength,
    wavenumber,
)


class TestConstants:
    """Test standard physical constants."""

    def test_speed_of_sound(self):
        """Speed of sound should be 343 m/s at 20°C."""
        # Literature: Kinsler et al. (1982), Table 1.1
        assert SPEED_OF_SOUND == 343.0

    def test_air_density(self):
        """Air density should be 1.18 kg/m³ at 20°C."""
        # Literature: Kinsler et al. (1982), Table 1.1
        assert AIR_DENSITY == 1.18

    def test_atmospheric_pressure(self):
        """Standard atmospheric pressure should be 101325 Pa."""
        assert ATMOSPHERIC_PRESSURE == 101325

    def test_characteristic_impedance(self):
        """Characteristic impedance should be ρc ≈ 405 rayl."""
        # Literature: Kinsler et al. (1982), Eq. 1.11
        # Z₀ = ρc = 1.18 × 343 ≈ 405
        expected = AIR_DENSITY * SPEED_OF_SOUND
        assert CHARACTERISTIC_IMPEDANCE_AIR == expected
        assert 400 < CHARACTERISTIC_IMPEDANCE_AIR < 410

    def test_pi(self):
        """PI constant should be accurate."""
        assert 3.14159 < PI < 3.14160


class TestWavenumber:
    """Test wavenumber calculation."""

    def test_wavenumber_1khz(self):
        """Wavenumber at 1 kHz should be approximately 18.3 rad/m."""
        # k = 2πf/c = 2π × 1000 / 343
        k = wavenumber(1000)
        expected = 2 * np.pi * 1000 / 343
        assert np.isclose(k, expected, rtol=0.001)
        assert 18.3 < k < 18.4

    def test_wavenumber_343hz(self):
        """Wavenumber at 343 Hz (λ = 1 m) should be 2π."""
        # k = 2πf/c = 2π × 343 / 343 = 2π
        k = wavenumber(343)
        assert np.isclose(k, 2 * np.pi, rtol=0.001)

    def test_wavenumber_custom_speed_of_sound(self):
        """Wavenumber should scale inversely with speed of sound."""
        k1 = wavenumber(1000, speed_of_sound=343)
        k2 = wavenumber(1000, speed_of_sound=400)
        assert k2 < k1  # Higher c → lower k
        assert np.isclose(k1 / k2, 400 / 343, rtol=0.001)

    def test_wavenumber_linear_scaling(self):
        """Wavenumber should scale linearly with frequency."""
        k1 = wavenumber(1000)
        k2 = wavenumber(2000)
        assert np.isclose(k2, 2 * k1, rtol=0.001)


class TestAngularFrequency:
    """Test angular frequency calculation."""

    def test_angular_frequency_1khz(self):
        """Angular frequency at 1 kHz should be approximately 6283 rad/s."""
        # ω = 2πf = 2π × 1000
        omega = angular_frequency(1000)
        expected = 2 * np.pi * 1000
        assert np.isclose(omega, expected, rtol=0.001)
        assert 6280 < omega < 6290

    def test_angular_frequency_linear_scaling(self):
        """Angular frequency should scale linearly with frequency."""
        omega1 = angular_frequency(1000)
        omega2 = angular_frequency(2000)
        assert np.isclose(omega2, 2 * omega1, rtol=0.001)


class TestWavelength:
    """Test wavelength calculation."""

    def test_wavelength_343hz(self):
        """Wavelength at 343 Hz should be 1 m."""
        # λ = c/f = 343/343 = 1
        lam = wavelength(343)
        assert np.isclose(lam, 1.0, rtol=0.001)

    def test_wavelength_1khz(self):
        """Wavelength at 1 kHz should be approximately 0.343 m."""
        # λ = c/f = 343/1000
        lam = wavelength(1000)
        expected = 343 / 1000
        assert np.isclose(lam, expected, rtol=0.001)
        assert 0.34 < lam < 0.35

    def test_wavelength_inverse_scaling(self):
        """Wavelength should scale inversely with frequency."""
        lam1 = wavelength(1000)
        lam2 = wavelength(2000)
        assert np.isclose(lam1, 2 * lam2, rtol=0.001)

    def test_wavelength_custom_speed_of_sound(self):
        """Wavelength should scale linearly with speed of sound."""
        lam1 = wavelength(1000, speed_of_sound=343)
        lam2 = wavelength(1000, speed_of_sound=400)
        assert lam2 > lam1  # Higher c → longer λ
        assert np.isclose(lam2 / lam1, 400 / 343, rtol=0.001)
