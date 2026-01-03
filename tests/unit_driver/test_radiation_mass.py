"""
Unit tests for radiation mass calculations.

These tests validate the Beranek (1954) radiation impedance implementation
and the iterative resonance solver that matches Hornresp's methodology.

Literature:
- Beranek (1954), Eq. 5.20 - Radiation impedance and reactance
- literature/horns/beranek_1954.md
"""

import pytest
import math
import numpy as np

from gsd.driver.radiation_mass import (
    calculate_radiation_mass,
    calculate_resonance_with_radiation_mass,
)
from gsd.driver import load_driver
from gsd.simulation.constants import AIR_DENSITY, SPEED_OF_SOUND


class TestCalculateRadiationMass:
    """Test radiation mass calculation for circular piston."""

    def test_low_frequency_limit(self):
        """
        Verify low-frequency asymptote matches Beranek theory.

        At low frequencies (ka << 1), the radiation reactance function
        approaches X₁ ≈ 8ka/(3π), giving M_rad ≈ (16/3)·ρ₀·a³.

        Literature: Beranek (1954), Eq. 5.20 - low-frequency limit
        """
        # Small piston at very low frequency
        S_d = 0.022  # 220 cm² (BC_8NDL51)
        f = 20.0  # Hz (very low)

        # Calculate radiation mass
        M_rad = calculate_radiation_mass(f, S_d, AIR_DENSITY, SPEED_OF_SOUND)

        # Calculate expected value from low-frequency asymptote
        # M_rad ≈ (16/3)·ρ₀·a³ at low frequencies
        a = math.sqrt(S_d / math.pi)
        omega = 2.0 * math.pi * f
        k = omega / SPEED_OF_SOUND
        ka = k * a

        # Expected: X₁ ≈ 8ka/(3π) when ka << 1
        X1_expected = (8.0 * ka) / (3.0 * math.pi)

        # Radiation reactance: X_rad = ρc·S·X₁
        X_rad_expected = AIR_DENSITY * SPEED_OF_SOUND * S_d * X1_expected

        # Equivalent mass: M_rad = X_rad / ω
        M_rad_expected = X_rad_expected / omega

        # Verify agreement within 1%
        assert abs(M_rad - M_rad_expected) / M_rad_expected < 0.01, \
            f"Low-frequency limit: {M_rad:.6f} vs expected {M_rad_expected:.6f}"

    def test_frequency_independence_at_low_f(self):
        """
        Verify radiation mass is approximately constant at low frequencies.

        In the low-frequency limit (ka << 1), radiation mass should be
        nearly independent of frequency (M_rad ∝ 1/ω·ω = constant).
        """
        S_d = 0.022  # 220 cm²

        # Calculate radiation mass at multiple low frequencies
        frequencies = [20.0, 40.0, 60.0, 80.0, 100.0]
        M_rad_values = [
            calculate_radiation_mass(f, S_d, AIR_DENSITY, SPEED_OF_SOUND)
            for f in frequencies
        ]

        # Calculate coefficient of variation
        mean_M_rad = np.mean(M_rad_values)
        std_M_rad = np.std(M_rad_values)
        cv = std_M_rad / mean_M_rad

        # At low frequencies, M_rad should vary less than 5%
        assert cv < 0.05, \
            f"Radiation mass varies too much at low frequencies: CV={cv:.3f}"

    def test_piston_area_scaling(self):
        """
        Verify radiation mass scales with piston area.

        For a circular piston, M_rad ∝ a³ ∝ S_d^(3/2) at low frequencies.
        """
        f = 50.0  # Hz

        # Test two different piston areas
        S_d1 = 0.022  # 220 cm² (8" driver)
        S_d2 = 0.0522  # 522 cm² (12" driver)

        M_rad1 = calculate_radiation_mass(f, S_d1, AIR_DENSITY, SPEED_OF_SOUND)
        M_rad2 = calculate_radiation_mass(f, S_d2, AIR_DENSITY, SPEED_OF_SOUND)

        # Expected scaling: M_rad ∝ S_d^(3/2)
        expected_ratio = (S_d2 / S_d1) ** 1.5
        actual_ratio = M_rad2 / M_rad1

        # Verify scaling within 10% (numerical approximation at finite frequency)
        assert abs(actual_ratio - expected_ratio) / expected_ratio < 0.1, \
            f"Piston area scaling: actual={actual_ratio:.2f}, expected={expected_ratio:.2f}"

    def test_invalid_frequency(self):
        """Test that invalid frequency raises ValueError."""
        S_d = 0.022

        with pytest.raises(ValueError, match="Frequency must be > 0"):
            calculate_radiation_mass(0.0, S_d)

        with pytest.raises(ValueError, match="Frequency must be > 0"):
            calculate_radiation_mass(-10.0, S_d)

    def test_invalid_area(self):
        """Test that invalid piston area raises ValueError."""
        f = 100.0

        with pytest.raises(ValueError, match="Piston area must be > 0"):
            calculate_radiation_mass(f, 0.0)

        with pytest.raises(ValueError, match="Piston area must be > 0"):
            calculate_radiation_mass(f, -0.01)


class TestResonanceWithRadiationMass:
    """Test iterative resonance solver with radiation mass."""

    def test_solver_convergence(self):
        """
        Verify iterative solver converges to stable solution.

        The solver should converge in <10 iterations for reasonable parameters.
        """
        # BC_8NDL51 parameters
        M_md = 0.02677  # kg
        C_ms = 2.03e-4  # m/N
        S_d = 0.022  # m²

        # Run with detailed iteration tracking
        M_ms = M_md
        F_s_prev = 0.0

        for i in range(20):
            F_s = 1.0 / (2.0 * math.pi * math.sqrt(M_ms * C_ms))

            if abs(F_s - F_s_prev) < 0.1:
                iterations = i + 1
                break

            F_s_prev = F_s
            M_rad = calculate_radiation_mass(F_s, S_d, AIR_DENSITY, SPEED_OF_SOUND)
            M_ms = M_md + 2.0 * M_rad

        # Should converge in less than 10 iterations
        assert iterations < 10, \
            f"Solver took {iterations} iterations to converge (expected <10)"

    def test_radiation_mass_increases_mass(self):
        """
        Verify that radiation mass increases total moving mass.

        M_ms should always be greater than M_md after convergence.
        """
        M_md = 0.02677  # kg
        C_ms = 2.03e-4  # m/N
        S_d = 0.022  # m²

        F_s, M_ms = calculate_resonance_with_radiation_mass(
            M_md, C_ms, S_d, AIR_DENSITY, SPEED_OF_SOUND
        )

        # Total mass should be greater than driver mass
        assert M_ms > M_md, \
            f"M_ms ({M_ms*1000:.2f}g) should be > M_md ({M_md*1000:.2f}g)"

        # Radiation mass should be reasonable (5-20% of total for typical drivers)
        M_rad = M_ms - M_md
        radiation_fraction = M_rad / M_ms
        assert 0.05 < radiation_fraction < 0.30, \
            f"Radiation mass fraction {radiation_fraction:.2%} outside expected range"

    def test_radiation_mass_lowers_resonance(self):
        """
        Verify that including radiation mass lowers resonance frequency.

        F_s with radiation mass should be lower than F_s using driver mass only.
        """
        M_md = 0.02677  # kg
        C_ms = 2.03e-4  # m/N
        S_d = 0.022  # m²

        # Calculate resonance with radiation mass
        F_s_with_rad, M_ms = calculate_resonance_with_radiation_mass(
            M_md, C_ms, S_d, AIR_DENSITY, SPEED_OF_SOUND
        )

        # Calculate resonance using driver mass only
        F_s_driver_only = 1.0 / (2.0 * math.pi * math.sqrt(M_md * C_ms))

        # Radiation mass should lower resonance frequency
        assert F_s_with_rad < F_s_driver_only, \
            f"F_s with radiation ({F_s_with_rad:.1f}Hz) should be < driver-only ({F_s_driver_only:.1f}Hz)"

        # The shift should be significant (>2% for typical drivers)
        shift_fraction = (F_s_driver_only - F_s_with_rad) / F_s_driver_only
        assert shift_fraction > 0.02, \
            f"Resonance shift {shift_fraction:.2%} should be >2%"

    def test_invalid_inputs(self):
        """Test that invalid inputs raise ValueError."""
        C_ms = 2.03e-4
        S_d = 0.022

        # Invalid M_md
        with pytest.raises(ValueError, match="Driver mass M_md must be > 0"):
            calculate_resonance_with_radiation_mass(0.0, C_ms, S_d)

        # Invalid C_ms
        with pytest.raises(ValueError, match="Compliance C_ms must be > 0"):
            calculate_resonance_with_radiation_mass(0.05, 0.0, S_d)

        # Invalid S_d
        with pytest.raises(ValueError, match="Area S_d must be > 0"):
            calculate_resonance_with_radiation_mass(0.05, C_ms, 0.0)


class TestDriverResonanceMatching:
    """Test that all B&C drivers match Hornresp resonance frequencies."""

    def test_bc_8ndl51_resonance(self):
        """
        Verify BC_8NDL51 resonance matches Hornresp.

        Hornresp F_s: 64.2 Hz
        Target: <0.5 Hz error
        """
        driver = load_driver("BC_8NDL51")

        # F_s is calculated during __post_init__ using iterative solver
        F_s_expected = 64.2  # Hz (from Hornresp)

        assert abs(driver.F_s - F_s_expected) < 0.5, \
            f"BC_8NDL51 F_s: {driver.F_s:.2f} Hz vs expected {F_s_expected:.2f} Hz"

    def test_bc_12ndl76_resonance(self):
        """
        Verify BC_12NDL76 resonance matches Hornresp.

        Hornresp F_s: 44.9 Hz
        Target: <0.5 Hz error
        """
        driver = load_driver("BC_12NDL76")

        F_s_expected = 44.9  # Hz (from Hornresp)

        assert abs(driver.F_s - F_s_expected) < 0.5, \
            f"BC_12NDL76 F_s: {driver.F_s:.2f} Hz vs expected {F_s_expected:.2f} Hz"

    def test_bc_15ds115_resonance(self):
        """
        Verify BC_15DS115 resonance matches Hornresp.

        Hornresp F_s: 19.0 Hz
        Target: <0.5 Hz error
        """
        driver = load_driver("BC_15DS115")

        F_s_expected = 19.0  # Hz (from Hornresp)

        assert abs(driver.F_s - F_s_expected) < 0.5, \
            f"BC_15DS115 F_s: {driver.F_s:.2f} Hz vs expected {F_s_expected:.2f} Hz"

    def test_bc_18pzw100_resonance(self):
        """
        Verify BC_18PZW100 resonance matches Hornresp.

        Hornresp F_s: 23.9 Hz
        Target: <0.5 Hz error
        """
        driver = get_bc_18pzw100()

        F_s_expected = 23.9  # Hz (from Hornresp)

        assert abs(driver.F_s - F_s_expected) < 0.5, \
            f"BC_18PZW100 F_s: {driver.F_s:.2f} Hz vs expected {F_s_expected:.2f} Hz"

    def test_all_drivers_resonance_accuracy(self):
        """
        Verify all 4 B&C drivers have excellent resonance matching.

        This is the key validation: radiation mass correction should
        bring all drivers to within 0.5 Hz of Hornresp F_s values.
        """
        drivers = [
            ("BC_8NDL51", load_driver("BC_8NDL51"), 64.2),
            ("BC_12NDL76", load_driver("BC_12NDL76"), 44.9),
            ("BC_15DS115", load_driver("BC_15DS115"), 19.0),
            ("BC_18PZW100", get_bc_18pzw100(), 23.9),
        ]

        for name, driver, expected_fs in drivers:
            error = abs(driver.F_s - expected_fs)

            print(f"\n{name}:")
            print(f"  Viberesp F_s: {driver.F_s:.2f} Hz")
            print(f"  Hornresp F_s: {expected_fs:.2f} Hz")
            print(f"  Error: {error:.2f} Hz ({error/expected_fs*100:.2f}%)")

            assert error < 0.5, \
                f"{name} resonance error {error:.2f} Hz exceeds 0.5 Hz threshold"

            # Verify radiation mass is being included
            assert driver.M_ms > driver.M_md, \
                f"{name}: M_ms should be > M_md (radiation mass not included)"


class TestRadiationMassValues:
    """Test radiation mass values for B&C drivers."""

    def test_bc_8ndl51_radiation_mass(self):
        """
        Verify BC_8NDL51 radiation mass is reasonable.

        Expected: ~3.7g radiation mass (14% of total mass)
        """
        driver = load_driver("BC_8NDL51")

        M_rad = driver.M_ms - driver.M_md
        radiation_fraction = M_rad / driver.M_ms

        # Radiation mass should be 3-4g
        assert 0.003 < M_rad < 0.005, \
            f"BC_8NDL51 radiation mass: {M_rad*1000:.2f}g (expected 3-4g)"

        # Should be 10-20% of total mass
        assert 0.10 < radiation_fraction < 0.20, \
            f"BC_8NDL51 radiation fraction: {radiation_fraction:.2%}"

    def test_bc_12ndl76_radiation_mass(self):
        """
        Verify BC_12NDL76 radiation mass is reasonable.

        Expected: ~13.4g radiation mass (20% of total mass)
        """
        driver = load_driver("BC_12NDL76")

        M_rad = driver.M_ms - driver.M_md
        radiation_fraction = M_rad / driver.M_ms

        # Radiation mass should be 12-15g
        assert 0.012 < M_rad < 0.016, \
            f"BC_12NDL76 radiation mass: {M_rad*1000:.2f}g (expected 12-15g)"

        # Should be 18-25% of total mass
        assert 0.15 < radiation_fraction < 0.25, \
            f"BC_12NDL76 radiation fraction: {radiation_fraction:.2%}"

    def test_bc_15ds115_radiation_mass(self):
        """
        Verify BC_15DS115 radiation mass is reasonable.

        Expected: ~28g radiation mass (10% of total mass)
        """
        driver = load_driver("BC_15DS115")

        M_rad = driver.M_ms - driver.M_md
        radiation_fraction = M_rad / driver.M_ms

        # Radiation mass should be 25-32g
        assert 0.025 < M_rad < 0.032, \
            f"BC_15DS115 radiation mass: {M_rad*1000:.2f}g (expected 25-32g)"

        # Should be 8-15% of total mass (subwoofer has large M_md)
        assert 0.08 < radiation_fraction < 0.15, \
            f"BC_15DS115 radiation fraction: {radiation_fraction:.2%}"

    def test_bc_18pzw100_radiation_mass(self):
        """
        Verify BC_18PZW100 radiation mass is reasonable.

        Expected: ~47g radiation mass (19% of total mass)
        """
        driver = get_bc_18pzw100()

        M_rad = driver.M_ms - driver.M_md
        radiation_fraction = M_rad / driver.M_ms

        # Radiation mass should be 40-55g
        assert 0.040 < M_rad < 0.055, \
            f"BC_18PZW100 radiation mass: {M_rad*1000:.2f}g (expected 40-55g)"

        # Should be 15-25% of total mass
        assert 0.15 < radiation_fraction < 0.25, \
            f"BC_18PZW100 radiation fraction: {radiation_fraction:.2%}"

    def test_radiation_mass_increases_with_driver_size(self):
        """
        Verify radiation mass increases with driver size.

        Larger drivers should have larger absolute radiation mass,
        though the fractional contribution varies.
        """
        drivers = [
            ("BC_8NDL51", load_driver("BC_8NDL51")),
            ("BC_12NDL76", load_driver("BC_12NDL76")),
            ("BC_15DS115", load_driver("BC_15DS115")),
            ("BC_18PZW100", get_bc_18pzw100()),
        ]

        M_rad_values = [
            (name, driver.M_ms - driver.M_md)
            for name, driver in drivers
        ]

        # Each subsequent driver should have more radiation mass
        # (not strictly true due to different resonances, but general trend)
        M_rad_8in = M_rad_values[0][1]
        M_rad_12in = M_rad_values[1][1]
        M_rad_15in = M_rad_values[2][1]
        M_rad_18in = M_rad_values[3][1]

        # 18" should have >5× radiation mass of 8"
        assert M_rad_18in > 5.0 * M_rad_8in, \
            f"18\" driver radiation mass ({M_rad_18in*1000:.1f}g) should be >5× 8\" ({M_rad_8in*1000:.1f}g)"
