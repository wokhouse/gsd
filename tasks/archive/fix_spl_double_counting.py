#!/usr/bin/env python3
"""
Fix the SPL calculation bug by removing double-counting of mechanical impedance.

Research from online agent identified that we're using Small's transfer function
which includes motional impedance in Ze, then dividing by Zm again.

Correct equation: v = (BL × V) / (Ze_electrical × Zm + BL²)

where Ze_electrical = Re + jωLe (NO motional component)

Literature:
- Small (1972) - Direct radiator analysis
- Research agent response: "SPL function of speed or acceleration" diyAudio
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import cmath
import math
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    helmholtz_resonance_frequency,
    calculate_optimal_port_dimensions,
)
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


def calculate_mechanical_impedance(
    frequency: float,
    driver,
    C_mb: float = None,
    radiation_multiplier: float = 2.0
) -> complex:
    """
    Calculate mechanical impedance Zm = Rms + jωMms + 1/(jωC)

    Literature:
        - Beranek (1954), Chapter 3 - Mechanical impedance
        - Small (1972), Eq. 3 - Mechanical circuit elements

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        C_mb: Box compliance (m/N). If None, uses driver C_ms
        radiation_multiplier: Multiplier for radiation mass (2.0 for infinite baffle)

    Returns:
        Complex mechanical impedance (N·s/m)
    """
    omega = 2 * math.pi * frequency

    # Use box compliance if provided, else driver compliance
    C_m = C_mb if C_mb is not None else driver.C_ms

    # Calculate radiation mass (frequency dependent)
    if radiation_multiplier > 0:
        from gsd.driver.radiation_mass import calculate_radiation_mass
        M_rad = calculate_radiation_mass(frequency, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
        M_ms = driver.M_md + radiation_multiplier * M_rad
    else:
        M_ms = driver.M_md

    # Mechanical impedance: R_ms + jωM_ms + 1/(jωC_m)
    # Beranek (1954), Eq. 3.2 (mechanical circuit elements)
    Z_m = driver.R_ms + complex(0, omega * M_ms) + complex(0, -1 / (omega * C_m))

    return Z_m


def calculate_diaphragm_velocity_correct(
    frequency: float,
    voltage: float,
    driver,
    C_mb: float = None
) -> complex:
    """
    Calculate diaphragm velocity using PROPER electromechanical coupling.

    CORRECT EQUATION (from research agent):
    v = (BL × V) / (Ze_electrical × Zm + BL²)

    where Ze_electrical = Re + jωLe (NO motional component!)

    Literature:
        - Small (1972), Eq. 8-10 - Electromechanical coupling
        - Beranek & Mellow (2012), Ch. 6 - Coupled electrical/mechanical circuits
        - Research agent: "SPL function of speed or acceleration" diyAudio

    CRITICAL FIX: Do NOT use Ze that includes motional impedance!
    The Ze from Small's transfer function already has (BL)²/Zm included.
    If we divide by Zm again, we're double-counting.

    Args:
        frequency: Frequency in Hz
        voltage: Input voltage (V)
        driver: ThieleSmallParameters instance
        C_mb: Box compliance (m/N). If None, uses driver C_ms

    Returns:
        Complex diaphragm velocity (m/s)
    """
    omega = 2 * math.pi * frequency

    # Electrical impedance WITHOUT motional component
    # Ze_electrical = Re + jωLe (voice coil only!)
    # literature/thiele_small/small_1972_closed_box.md
    Z_e_electrical = complex(driver.R_e, omega * driver.L_e)

    # Mechanical impedance (full mechanical circuit)
    Z_m = calculate_mechanical_impedance(frequency, driver, C_mb)

    # PROPER electromechanical coupling equation
    # v = (BL × V) / (Ze_electrical × Zm + BL²)
    # Small (1972), Eq. 8-10
    # Research agent derivation from diyAudio discussion
    numerator = driver.BL * voltage
    denominator = Z_e_electrical * Z_m + driver.BL**2

    velocity = numerator / denominator

    return velocity


def calculate_spl_from_velocity(
    frequency: float,
    velocity: complex,
    driver,
    measurement_distance: float = 1.0
) -> float:
    """
    Calculate SPL from diaphragm velocity (PRESSURE FORMULA IS CORRECT).

    Uses baffled piston radiation formula:
    p = ρ₀ × Sd × ω × |v| / (2πr)

    Literature:
        - Kinsler et al. (1982), Section 7.4 - Piston radiation
        - Beranek (1954), Chapter 5 - Radiation impedance
        - Research agent: "Your pressure formula is correct"

    Args:
        frequency: Frequency in Hz
        velocity: Complex diaphragm velocity (m/s)
        driver: ThieleSmallParameters instance
        measurement_distance: Measurement distance (m)

    Returns:
        SPL in dB
    """
    omega = 2 * math.pi * frequency

    # Volume velocity magnitude
    volume_velocity_mag = abs(velocity) * driver.S_d

    # Far-field pressure magnitude (baffled piston / half-space monopole)
    # p = ρ₀ × ω × U / (2πr)
    # Kinsler et al. (1982), Section 7.4
    # Research agent: "This equation is exactly correct"
    pressure_amplitude = (AIR_DENSITY * omega * volume_velocity_mag) / \
                         (2 * math.pi * measurement_distance)

    # Sound pressure level
    p_ref = 20e-6  # Reference pressure (Pa)
    spl = 20 * math.log10(max(pressure_amplitude, 1e-20) / p_ref)

    return spl


def test_fixed_spl():
    """Test the fixed SPL calculation."""
    print("=" * 70)
    print("FIXED SPL CALCULATION TEST: BC_15DS115")
    print("=" * 70)

    driver = get_bc_15ds115()

    # Design parameters (180L @ 28Hz)
    Vb = 0.180
    Fb = 28.0

    # Calculate box compliance (for ported box)
    alpha = driver.V_as / Vb
    C_mb = driver.C_ms / (1.0 + alpha)

    # BUT for proper velocity calculation, we should use DRIVER C_ms
    # because the research agent's equation is for direct radiator
    # Let's test both to see the difference

    print(f"\nDesign: Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz")
    print(f"Compliance ratio α = {alpha:.2f}")
    print(f"Box compliance C_mb = {C_mb*1e6:.2f} mm/N")

    # Test frequencies
    test_freqs = [10, 20, 28, 40, 50, 70, 100, 150, 200, 500, 1000]

    print("\n" + "=" * 70)
    print("FIXED RESPONSE (Proper coupling, no double-counting)")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | {'Velocity (mm/s)':>15} | {'SPL (dB)':>10} | {'Note'}")
    print("-" * 70)

    results = []
    for freq in test_freqs:
        # Calculate velocity with CORRECT method
        velocity = calculate_diaphragm_velocity_correct(freq, 2.83, driver, C_mb)
        velocity_mag = abs(velocity)

        # Calculate SPL
        spl = calculate_spl_from_velocity(freq, velocity, driver)

        note = ""
        if freq < Fb / math.sqrt(2):
            note = "Below tuning (rolloff)"
        elif abs(freq - Fb) < 2:
            note = "AT TUNING"
        elif freq < driver.F_s:
            note = "Between Fs and Fb"
        elif freq < 200:
            note = "Passband (should be ~flat)"
        else:
            note = "High freq (rolloff)"

        print(f"{freq:>10.1f} | {velocity_mag*1000:>15.3f} | {spl:>10.1f} | {note}")
        results.append((freq, velocity_mag, spl))

    # Check for proper behavior
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    # Extract arrays
    freqs = np.array([r[0] for r in results])
    vels = np.array([r[1] for r in results])
    spls = np.array([r[2] for r in results])

    # Check 1: Velocity should peak near Fs then fall
    fs_idx = np.argmin(np.abs(freqs - driver.F_s))
    peak_vel_idx = np.argmax(vels)
    peak_vel_freq = freqs[peak_vel_idx]

    print(f"\n✓ Velocity Check:")
    print(f"  Driver Fs: {driver.F_s:.1f} Hz")
    print(f"  Peak velocity at: {peak_vel_freq:.1f} Hz")
    print(f"  Peak magnitude: {vels[peak_vel_idx]*1000:.3f} mm/s")

    if peak_vel_freq < driver.F_s * 1.5:
        print(f"  ✓ Peak is near Fs (correct!)")
    else:
        print(f"  ✗ Peak is far from Fs (problem!)")

    # Check 2: Velocity should fall above Fs (mass-controlled)
    above_fs = freqs > driver.F_s
    if np.any(above_fs):
        # Check slope from Fs to 200 Hz
        fs_vel = vels[fs_idx]
        vel_200 = vels[np.argmin(np.abs(freqs - 200))]

        # Expected: velocity should fall roughly as 1/f
        # From 33 Hz to 200 Hz: 200/33 ≈ 6× frequency increase
        # Velocity should fall by ~6× (or 16 dB)
        expected_fall = 200 / driver.F_s
        actual_fall = fs_vel / vel_200 if vel_200 > 0 else float('inf')

        print(f"\n✓ Mass-Controlled Rolloff Check:")
        print(f"  Velocity at Fs ({driver.F_s:.1f} Hz): {fs_vel*1000:.3f} mm/s")
        print(f"  Velocity at 200 Hz: {vel_200*1000:.3f} mm/s")
        print(f"  Actual fall: {actual_fall:.2f}×")
        print(f"  Expected fall: {expected_fall:.2f}× (mass-controlled, 1/f)")

        if 0.5 * expected_fall < actual_fall < 2.0 * expected_fall:
            print(f"  ✓ Velocity falling correctly (mass-controlled)")
        else:
            print(f"  ⚠ Velocity fall not matching 1/f (may need adjustment)")

    # Check 3: SPL should be relatively flat in passband
    passband = (freqs >= Fb) & (freqs <= 200)
    if np.any(passband):
        passband_spl = spls[passband]
        spl_range = np.max(passband_spl) - np.min(passband_spl)

        print(f"\n✓ SPL Flatness Check:")
        print(f"  Passband ({Fb:.1f}-{200:.1f} Hz) SPL range: {spl_range:.1f} dB")

        if spl_range < 10:
            print(f"  ✓ Relatively flat (good!)")
        else:
            print(f"  ⚠ Large variation (may need adjustment)")

    # Check 4: SPL should rolloff at high frequencies
    if freqs[-1] > 500:
        spl_200 = spls[np.argmin(np.abs(freqs - 200))]
        spl_500 = spls[np.argmin(np.abs(freqs - 500))]
        spl_diff = spl_500 - spl_200

        print(f"\n✓ High-Frequency Rolloff Check:")
        print(f"  SPL at 200 Hz: {spl_200:.1f} dB")
        print(f"  SPL at 500 Hz: {spl_500:.1f} dB")
        print(f"  Difference: {spl_diff:+.1f} dB")

        if spl_diff < -3:
            print(f"  ✓ Rolloff at high frequencies (correct!)")
        else:
            print(f"  ✗ Not rolling off (problem!)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_fixed_spl()
