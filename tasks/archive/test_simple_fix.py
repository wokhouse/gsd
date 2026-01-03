#!/usr/bin/env python3
"""
Test the fix with INFINITE BAFFLE (simplest case).

Research agent's equation is for direct radiator, not ported box.
Let's test with infinite baffle first to verify the physics works.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import cmath
import math
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


def calculate_mechanical_impedance_ib(
    frequency: float,
    driver
) -> complex:
    """Calculate mechanical impedance for infinite baffle."""
    omega = 2 * math.pi * frequency

    # Infinite baffle: 2× radiation mass
    from gsd.driver.radiation_mass import calculate_radiation_mass
    M_rad = calculate_radiation_mass(frequency, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
    M_ms = driver.M_md + 2.0 * M_rad

    # Zm = Rms + jωMms + 1/(jωCms)
    Z_m = driver.R_ms + complex(0, omega * M_ms) + complex(0, -1 / (omega * driver.C_ms))

    return Z_m


def calculate_velocity_ib(frequency: float, voltage: float, driver) -> complex:
    """
    Calculate velocity using RESEARCH AGENT'S equation:

    v = (BL × V) / (Ze_electrical × Zm + BL²)

    where Ze_electrical = Re + jωLe (NO motional!)
    """
    omega = 2 * math.pi * frequency

    # Electrical impedance (voice coil ONLY, no motional)
    Z_e_electrical = complex(driver.R_e, omega * driver.L_e)

    # Mechanical impedance
    Z_m = calculate_mechanical_impedance_ib(frequency, driver)

    # PROPER coupling equation from research agent
    numerator = driver.BL * voltage
    denominator = Z_e_electrical * Z_m + driver.BL**2

    velocity = numerator / denominator
    return velocity


def calculate_spl(frequency: float, velocity: complex, driver) -> float:
    """Calculate SPL from velocity (pressure formula is correct)."""
    omega = 2 * math.pi * frequency

    volume_velocity_mag = abs(velocity) * driver.S_d
    pressure_amplitude = (AIR_DENSITY * omega * volume_velocity_mag) / (2 * math.pi)
    p_ref = 20e-6
    spl = 20 * math.log10(max(pressure_amplitude, 1e-20) / p_ref)

    return spl


def main():
    """Test infinite baffle (simplest case)."""
    print("=" * 70)
    print("TEST: INFINITE BAFFLE (Simplest Direct Radiator)")
    print("=" * 70)

    driver = get_bc_15ds115()

    test_freqs = [10, 20, 33, 50, 70, 100, 150, 200, 500, 1000]

    print(f"\nDriver parameters:")
    print(f"  Fs: {driver.F_s:.1f} Hz")
    print(f"  M_md: {driver.M_md*1000:.1f} g")
    print(f"  C_ms: {driver.C_ms*1e6:.2f} mm/N")
    print(f"  BL: {driver.BL:.1f} T·m")
    print(f"  R_e: {driver.R_e:.1f} Ω")
    print(f"  L_e: {driver.L_e*1000:.1f} mH")

    print("\n" + "=" * 70)
    print("RESPONSE (Research Agent's Equation)")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | {'Velocity (mm/s)':>15} | {'SPL (dB)':>10} | {'Note'}")
    print("-" * 70)

    results = []
    for freq in test_freqs:
        velocity = calculate_velocity_ib(freq, 2.83, driver)
        spl = calculate_spl(freq, velocity, driver)

        if freq < driver.F_s:
            note = "Below Fs"
        elif abs(freq - driver.F_s) < 5:
            note = "NEAR Fs (resonance)"
        elif freq < 200:
            note = "Mass-controlled (should fall)"
        else:
            note = "High freq (should rolloff)"

        print(f"{freq:>10.1f} | {abs(velocity)*1000:>15.3f} | {spl:>10.1f} | {note}")
        results.append((freq, abs(velocity), spl))

    # Check behavior
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    freqs = np.array([r[0] for r in results])
    vels = np.array([r[1] for r in results])
    spls = np.array([r[2] for r in results])

    # Velocity should peak near Fs
    peak_idx = np.argmax(vels)
    peak_freq = freqs[peak_idx]
    print(f"\n1. Velocity peak:")
    print(f"   Expected: Near Fs ({driver.F_s:.1f} Hz)")
    print(f"   Actual: {peak_freq:.1f} Hz")
    if abs(peak_freq - driver.F_s) < driver.F_s * 0.5:
        print(f"   ✓ PASS: Peak is near Fs")
    else:
        print(f"   ✗ FAIL: Peak is far from Fs")

    # Velocity should fall above Fs (mass-controlled)
    fs_idx = np.argmin(np.abs(freqs - driver.F_s))
    idx_200 = np.argmin(np.abs(freqs - 200))
    vel_fs = vels[fs_idx]
    vel_200 = vels[idx_200]
    fall_ratio = vel_fs / vel_200 if vel_200 > 0 else float('inf')

    print(f"\n2. Mass-controlled rolloff:")
    print(f"   Velocity at Fs: {vel_fs*1000:.3f} mm/s")
    print(f"   Velocity at 200 Hz: {vel_200*1000:.3f} mm/s")
    print(f"   Fall ratio: {fall_ratio:.2f}×")
    print(f"   Expected: ~{200/driver.F_s:.2f}× (200/Fs)")
    if 0.5 * (200/driver.F_s) < fall_ratio < 2.0 * (200/driver.F_s):
        print(f"   ✓ PASS: Correct 1/f rolloff")
    else:
        print(f"   ✗ FAIL: Not following 1/f")

    # SPL should be relatively flat above Fs
    above_fs = freqs >= driver.F_s
    above_200 = freqs[above_fs & (freqs <= 200)]
    spl_above_200 = spls[above_fs & (freqs <= 200)]

    if len(spl_above_200) > 0:
        spl_range = np.max(spl_above_200) - np.min(spl_above_200)
        print(f"\n3. SPL flatness ({driver.F_s:.0f}-{200:.0f} Hz):")
        print(f"   Range: {spl_range:.1f} dB")
        if spl_range < 6:
            print(f"   ✓ PASS: Relatively flat")
        else:
            print(f"   ✗ FAIL: Too much variation")

    # SPL should rolloff at high frequencies
    spl_200 = spls[idx_200]
    idx_500 = np.argmin(np.abs(freqs - 500))
    spl_500 = spls[idx_500]
    diff = spl_500 - spl_200

    print(f"\n4. High-frequency rolloff:")
    print(f"   SPL at 200 Hz: {spl_200:.1f} dB")
    print(f"   SPL at 500 Hz: {spl_500:.1f} dB")
    print(f"   Difference: {diff:+.1f} dB")
    if diff < -3:
        print(f"   ✓ PASS: Rolloff at HF")
    else:
        print(f"   ✗ FAIL: Not rolling off")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
