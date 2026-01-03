#!/usr/bin/env python3
"""
Debug Small's transfer function for ported box impedance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import cmath
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import calculate_optimal_port_dimensions


def debug_transfer_function_at_f(freq, driver, Vb, Fb, Qp=7.0):
    """Debug the transfer function calculation at a specific frequency."""
    print(f"\n{'='*70}")
    print(f"FREQUENCY: {freq} Hz")
    print(f"{'='*70}")

    # Small (1973): Normalized parameters
    omega_s = 2 * math.pi * driver.F_s
    omega_p = 2 * math.pi * Fb
    Ts = 1.0 / omega_s
    Tp = 1.0 / omega_p
    alpha = driver.V_as / Vb
    h = Fb / driver.F_s

    print(f"\nTime constants:")
    print(f"  Ts = {Ts:.6f} s")
    print(f"  Tp = {Tp:.6f} s")
    print(f"  alpha = {alpha:.3f}")
    print(f"  h = {h:.3f}")

    # Calculate R_es (motional resistance)
    R_ms = omega_s * driver.M_ms / driver.Q_ms
    R_es = (driver.BL ** 2) / R_ms
    print(f"\nMotional resistance:")
    print(f"  R_ms = {R_ms:.3f} N·s/m")
    print(f"  R_es = {R_es:.1f} Ω")

    # Complex frequency variable
    omega = 2 * math.pi * freq
    s = complex(0, omega)
    print(f"\nComplex frequency:")
    print(f"  omega = {omega:.1f} rad/s")
    print(f"  s = j{omega:.1f}")

    # Port polynomial
    port_poly = (s ** 2) * (Tp ** 2) + s * (Tp / Qp) + 1
    print(f"\nPort polynomial (creates dip at Fb):")
    print(f"  port_poly = {port_poly}")
    print(f"  |port_poly| = {abs(port_poly):.3f}")

    # Numerator
    numerator = (s * Tp / driver.Q_es) * port_poly
    print(f"\nNumerator N(s):")
    print(f"  N(s) = {numerator}")
    print(f"  |N(s)| = {abs(numerator):.3f}")

    # Denominator coefficients
    a4 = (Ts ** 2) * (Tp ** 2)
    a3 = (Tp ** 2 * Ts / Qp) + (Ts * Tp ** 2 / driver.Q_es)
    a2 = (alpha + 1) * (Tp ** 2) + (Ts * Tp / (Qp * driver.Q_es)) + (Ts ** 2)
    a1 = Tp / Qp + Ts / driver.Q_es
    a0 = 1

    print(f"\nDenominator coefficients:")
    print(f"  a4 (s⁴) = {a4:.2e}")
    print(f"  a3 (s³) = {a3:.4f}")
    print(f"  a2 (s²) = {a2:.6f}")
    print(f"  a1 (s¹) = {a1:.4f}")
    print(f"  a0 (s⁰) = {a0:.1f}")

    # Full denominator
    denominator = (s ** 4) * a4 + (s ** 3) * a3 + (s ** 2) * a2 + s * a1 + a0
    print(f"\nDenominator D'(s):")
    print(f"  D'(s) = {denominator}")
    print(f"  |D'(s)| = {abs(denominator):.3f}")

    # Calculate impedance
    if abs(denominator) == 0:
        Z_vc = complex(driver.R_e, float('inf'))
    else:
        ratio = numerator / denominator
        Z_vc = complex(driver.R_e, 0) + R_es * ratio

    print(f"\nImpedance calculation:")
    print(f"  N(s) / D'(s) = {numerator / denominator}")
    print(f"  R_es × (N/D) = {R_es * (numerator / denominator)}")
    print(f"  Z_vc = Re + R_es × (N/D) = {Z_vc}")
    print(f"  |Z_vc| = {abs(Z_vc):.1f} Ω")

    # Add voice coil inductance
    omega = 2 * math.pi * freq
    Z_total = Z_vc + complex(0, omega * driver.L_e)
    print(f"\nWith voice coil inductance:")
    print(f"  jωLe = j{omega * driver.L_e:.1f} Ω")
    print(f"  Z_total = {Z_total}")
    print(f"  |Z_total| = {abs(Z_total):.1f} Ω")

    return abs(Z_total)


def main():
    """Debug transfer function at multiple frequencies."""
    print("=" * 70)
    print("DEBUG SMALL'S TRANSFER FUNCTION FOR PORTED BOX")
    print("=" * 70)

    driver = get_bc_15ds115()

    print(f"\nDriver: BC_15DS115")
    print(f"  Re = {driver.R_e:.2f} Ω")
    print(f"  Qes = {driver.Q_es:.3f}")
    print(f"  Qms = {driver.Q_ms:.3f}")
    print(f"  BL = {driver.BL:.1f} T·m")

    # B4 alignment
    Vb = driver.V_as
    Fb = driver.F_s

    print(f"\nBox: B4 alignment")
    print(f"  Vb = {Vb*1000:.1f} L")
    print(f"  Fb = {Fb:.1f} Hz")

    # Test at key frequencies
    test_freqs = [20, 30, 33, 40, 50, 100]

    for freq in test_freqs:
        debug_transfer_function_at_f(freq, driver, Vb, Fb, Qp=7.0)

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    print("\nExpected Hornresp values:")
    print("  20 Hz: ~140 Ω")
    print("  30 Hz: ~5 Ω (dip)")
    print("  33 Hz: ~14 Ω")
    print("  40 Hz: ~46 Ω")
    print("  50 Hz: ~119 Ω")
    print("  100 Hz: ~39 Ω")

    print("\nIf values are all ~150 Ω:")
    print("  - Denominator polynomial may be evaluating incorrectly")
    print("  - Check Q_es value (0.06 is very low)")
    print("  - May be numerical precision issue with extreme driver")


if __name__ == "__main__":
    main()
