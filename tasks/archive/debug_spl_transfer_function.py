#!/usr/bin/env python3
"""
Debug SPL transfer function calculation for ported box.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_optimal_port_dimensions
)


def load_hornresp_data(filepath):
    """Load Hornresp simulation results from text file."""
    frequencies = []
    spl_values = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines[2:]:  # Skip header
        parts = line.split()
        if len(parts) >= 6:
            try:
                freq = float(parts[0])
                spl = float(parts[4])
                frequencies.append(freq)
                spl_values.append(spl)
            except ValueError:
                continue

    return np.array(frequencies), np.array(spl_values)


def debug_spl_at_f(freq, driver, Vb, Fb, voltage=2.83):
    """Debug SPL calculation at a specific frequency."""
    print(f"\n{'='*70}")
    print(f"FREQUENCY: {freq} Hz")
    print(f"{'='*70}")

    # System parameters
    omega_s = 2 * math.pi * driver.F_s
    omega_b = 2 * math.pi * Fb
    Ts = 1.0 / omega_s
    Tb = 1.0 / omega_b
    alpha = driver.V_as / Vb
    Qp = 7.0

    # Complex frequency
    omega = 2 * math.pi * freq
    s = complex(0, omega)

    # Denominator polynomial D'(s)
    a4 = (Ts ** 2) * (Tb ** 2)
    a3 = (Tb ** 2 * Ts / Qp) + (Tb * Ts ** 2 / driver.Q_es)
    a2 = (alpha + 1) * (Tb ** 2) + (Ts * Tb / (Qp * driver.Q_es)) + (Ts ** 2)
    a1 = Tb / Qp + Ts / driver.Q_es
    a0 = 1

    denominator = (s ** 4) * a4 + (s ** 3) * a3 + (s ** 2) * a2 + s * a1 + a0

    # Numerator for pressure response
    numerator_port = (s ** 2) * (Tb ** 2) + s * (Tb / Qp) + 1

    # Transfer function magnitude
    if abs(denominator) == 0:
        G = complex(0, 0)
    else:
        G = numerator_port / denominator

    G_mag = abs(G)
    G_dB = 20 * math.log10(G_mag) if G_mag > 0 else -float('inf')

    print(f"\nTransfer function:")
    print(f"  |G(s)| = {G_mag:.6f}")
    print(f"  20·log₁₀(|G|) = {G_dB:.2f} dB")

    # Reference efficiency
    eta_0 = (1.18 / (2 * math.pi * 343)) * \
            ((4 * math.pi ** 2 * driver.F_s ** 3 * driver.V_as) / driver.Q_es)

    eta = eta_0 / (1.0 + alpha)

    print(f"\nEfficiency:")
    print(f"  η₀ = {eta_0:.6f}")
    print(f"  η = {eta:.6f}")

    # Reference power
    R_nominal = driver.R_e
    P_ref = (voltage ** 2) / R_nominal

    # Reference pressure
    p_ref = 20e-6
    pressure_rms = math.sqrt(eta * P_ref * 1.18 * 343 / (4 * math.pi * 1.0 ** 2))
    spl_ref_uncal = 20 * math.log10(pressure_rms / p_ref) if pressure_rms > 0 else 0

    # Apply calibration
    CALIBRATION_OFFSET_DB = -25.25
    spl_ref = spl_ref_uncal + CALIBRATION_OFFSET_DB

    print(f"\nReference SPL:")
    print(f"  Uncalibrated: {spl_ref_uncal:.2f} dB")
    print(f"  After calibration (-25.25 dB): {spl_ref:.2f} dB")

    # Total SPL
    spl = spl_ref + G_dB

    print(f"\nTotal SPL:")
    print(f"  SPL = {spl_ref:.2f} + {G_dB:.2f} = {spl:.2f} dB")

    return spl


def main():
    """Debug SPL calculation at multiple frequencies."""
    print("=" * 70)
    print("DEBUG SPL TRANSFER FUNCTION FOR PORTED BOX")
    print("=" * 70)

    driver = get_bc_15ds115()
    Vb = driver.V_as
    Fb = driver.F_s

    print(f"\nDriver: BC_15DS115")
    print(f"  Re = {driver.R_e:.2f} Ω")
    print(f"  Qes = {driver.Q_es:.3f}")
    print(f"  Fs = {driver.F_s:.1f} Hz")
    print(f"  Vas = {driver.V_as*1000:.1f} L")

    # Load Hornresp data
    hornresp_file = "imports/bc15ds115_b4_alignment_sim.txt"
    hornresp_freq, hornresp_spl = load_hornresp_data(hornresp_file)

    # Test at key frequencies
    test_freqs = [20, 30, 33, 40, 50, 70, 100, 150, 200]

    print(f"\n{'='*70}")
    print("SPL COMPARISON")
    print(f"{'='*70}")
    print(f"{'Freq (Hz)':>10} | {'Viberesp SPL':>13} | {'Hornresp SPL':>13} | {'Diff':>7} | {'Transfer Func (dB)':>19}")
    print("-" * 70)

    for freq in test_freqs:
        spl_viberesp = debug_spl_at_f(freq, driver, Vb, Fb)

        # Get Hornresp value
        idx = np.argmin(np.abs(hornresp_freq - freq))
        spl_hornresp = hornresp_spl[idx]
        diff = spl_viberesp - spl_hornresp

        # Get transfer function contribution
        omega_s = 2 * math.pi * driver.F_s
        omega_b = 2 * math.pi * Fb
        Ts = 1.0 / omega_s
        Tb = 1.0 / omega_b
        alpha = driver.V_as / Vb
        Qp = 7.0

        omega = 2 * math.pi * freq
        s = complex(0, omega)

        a4 = (Ts ** 2) * (Tb ** 2)
        a3 = (Tb ** 2 * Ts / Qp) + (Tb * Ts ** 2 / driver.Q_es)
        a2 = (alpha + 1) * (Tb ** 2) + (Ts * Tb / (Qp * driver.Q_es)) + (Ts ** 2)
        a1 = Tb / Qp + Ts / driver.Q_es
        a0 = 1

        denominator = (s ** 4) * a4 + (s ** 3) * a3 + (s ** 2) * a2 + s * a1 + a0
        numerator_port = (s ** 2) * (Tb ** 2) + s * (Tb / Qp) + 1

        G_mag = abs(numerator_port / denominator) if abs(denominator) > 0 else 0
        G_dB = 20 * math.log10(G_mag) if G_mag > 0 else -float('inf')

        print(f"{freq:>10.1f} | {spl_viberesp:>13.1f} | {spl_hornresp:>13.1f} | {diff:>+7.1f} | {G_dB:>19.2f}")

    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    print("\nIf transfer function is wrong:")
    print("  - Check denominator polynomial coefficients")
    print("  - Verify Q_ES value (0.06 is very low)")
    print("  - May need to use different model for high-BL drivers")

    print("\nIf transfer function is correct but reference is wrong:")
    print("  - Efficiency calculation may have bug")
    print("  - Calibration offset may need adjustment")


if __name__ == "__main__":
    main()
