#!/usr/bin/env python3
"""
Test with a lower BL driver to see if the equation works better.

BC_15DS115 has BL=38.7 which gives BL²=1498 (very high).
This might be causing the velocity to stay constant.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
from gsd.driver.bc_drivers import get_bc_8ndl51
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


def test_driver(driver, name):
    """Test a driver."""
    print("\n" + "=" * 70)
    print(f"DRIVER: {name}")
    print("=" * 70)

    print(f"\nParameters:")
    print(f"  Fs: {driver.F_s:.1f} Hz")
    print(f"  M_md: {driver.M_md*1000:.1f} g")
    print(f"  C_ms: {driver.C_ms*1e6:.2f} mm/N")
    print(f"  BL: {driver.BL:.1f} T·m  →  BL² = {driver.BL**2:.1f}")
    print(f"  R_e: {driver.R_e:.1f} Ω")
    print(f"  L_e: {driver.L_e*1000:.1f} mH")

    # Test frequencies
    test_freqs = [driver.F_s, driver.F_s*2, driver.F_s*6]

    print(f"\n{'Freq (Hz)':>10} | {'M_ms (g)':>10} | {'|Zm| (Ω)':>10} | {'|vel| (mm/s)':>12}")
    print("-" * 70)

    for freq in test_freqs:
        omega = 2 * math.pi * freq

        # Calculate mechanical impedance
        from gsd.driver.radiation_mass import calculate_radiation_mass
        M_rad = calculate_radiation_mass(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
        M_ms = driver.M_md + 2.0 * M_rad

        Zm_massive = omega * M_ms
        Zm_compliant = -1 / (omega * driver.C_ms)
        Zm = complex(driver.R_ms, Zm_massive + Zm_compliant)

        # Electrical impedance
        Ze = complex(driver.R_e, omega * driver.L_e)

        # Velocity using research agent's equation
        numerator = driver.BL * 2.83
        denominator = Ze * Zm + driver.BL**2
        velocity = numerator / denominator

        print(f"{freq:>10.1f} | {M_ms*1000:>10.2f} | {abs(Zm):>10.2f} | {abs(velocity)*1000:>12.3f}")

    # Check rolloff
    omega1 = 2 * math.pi * driver.F_s
    omega2 = 2 * math.pi * (driver.F_s * 6)

    from gsd.driver.radiation_mass import calculate_radiation_mass
    M_rad1 = calculate_radiation_mass(driver.F_s, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
    M_ms1 = driver.M_md + 2.0 * M_rad1
    Zm1 = complex(driver.R_ms, omega1 * M_ms1 + (-1 / (omega1 * driver.C_ms)))

    M_rad2 = calculate_radiation_mass(driver.F_s*6, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
    M_ms2 = driver.M_md + 2.0 * M_rad2
    Zm2 = complex(driver.R_ms, omega2 * M_ms2 + (-1 / (omega2 * driver.C_ms)))

    Ze1 = complex(driver.R_e, omega1 * driver.L_e)
    Ze2 = complex(driver.R_e, omega2 * driver.L_e)

    vel1 = (driver.BL * 2.83) / (Ze1 * Zm1 + driver.BL**2)
    vel2 = (driver.BL * 2.83) / (Ze2 * Zm2 + driver.BL**2)

    freq_ratio = 6
    vel_ratio = abs(vel1) / abs(vel2)
    expected_ratio = freq_ratio  # Should fall as 1/f

    print(f"\nRolloff check (Fs → 6×Fs):")
    print(f"  Frequency increase: {freq_ratio:.1f}×")
    print(f"  Velocity decrease: {vel_ratio:.2f}×")
    print(f"  Expected decrease: ~{expected_ratio:.1f}× (mass-controlled)")

    if 0.5 * expected_ratio < vel_ratio < 2.0 * expected_ratio:
        print(f"  ✓ PASS: Good mass-controlled rolloff")
    else:
        print(f"  ✗ FAIL: Not following 1/f rolloff")
        print(f"  Issue: BL²={driver.BL**2:.1f} might be dominating denominator")

        # Check if BL² dominates
        mag_ZeZm1 = abs(Ze1 * Zm1)
        mag_ZeZm2 = abs(Ze2 * Zm2)

        print(f"\n  Denominator analysis:")
        print(f"    At Fs: |Ze×Zm| = {mag_ZeZm1:.1f}, BL² = {driver.BL**2:.1f}")
        print(f"    At 6Fs: |Ze×Zm| = {mag_ZeZm2:.1f}, BL² = {driver.BL**2:.1f}")

        if mag_ZeZm1 < driver.BL**2 and mag_ZeZm2 < driver.BL**2:
            print(f"    → BL² dominates both (velocity will be constant)")
        elif mag_ZeZm1 > driver.BL**2 or mag_ZeZm2 > driver.BL**2:
            print(f"    → Ze×Zm is significant (proper coupling)")


def main():
    """Test multiple drivers."""
    print("=" * 70)
    print("COMPARISON: High BL vs Low BL Drivers")
    print("=" * 70)

    # High BL driver (problematic)
    from gsd.driver.bc_drivers import get_bc_15ds115
    test_driver(get_bc_15ds115(), "BC_15DS115 (High BL: 38.7)")

    # Low BL driver (might work better)
    test_driver(get_bc_8ndl51(), "BC_8NDL51 (Low BL: 7.3)")


if __name__ == "__main__":
    main()
