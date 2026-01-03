#!/usr/bin/env python3
"""
Debug efficiency calculation for ported box.

According to Small (1972), the reference efficiency formula is:
η₀ = (ρ₀/2πc) × (4π²Fs³Vas/Qes)

But this formula needs proper unit conversions!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
from gsd.driver.bc_drivers import get_bc_15ds115


def debug_efficiency():
    """Debug efficiency calculation."""
    print("=" * 70)
    print("EFFICIENCY CALCULATION DEBUG")
    print("=" * 70)

    driver = get_bc_15ds115()

    print(f"\nDriver Parameters:")
    print(f"  Fs = {driver.F_s} Hz")
    print(f"  Vas = {driver.V_as} m³ = {driver.V_as*1000} L")
    print(f"  Qes = {driver.Q_es}")
    print(f"  Sd = {driver.S_d} m² = {driver.S_d*10000} cm²")

    # Constants
    air_density = 1.18  # kg/m³
    speed_of_sound = 343  # m/s

    # Current formula (WRONG)
    eta_0_wrong = (air_density / (2 * math.pi * speed_of_sound)) * \
                  ((4 * math.pi ** 2 * driver.F_s ** 3 * driver.V_as) / driver.Q_es)

    print(f"\nCurrent formula (WRONG):")
    print(f"  η₀ = {eta_0_wrong:.6f}")
    print(f"  This is {eta_0_wrong*100:.1f}% efficiency - IMPOSSIBLE!")

    # Small's formula from JAES 1972
    # η₀ = (ρ₀/2πc) × (4π²Fs³Vas/Qes)
    # But this needs to be dimensionless!
    #
    # According to Small (1972), the correct formula is:
    # η₀ = (4π²/c³) × (Fs³Vas/Qes)
    #
    # Or equivalently:
    # η₀ = (ρ₀/4πc) × ((2πFs)³Vas/Qes) / (ρ₀c²)
    # where the denominator ρ₀c² is the characteristic acoustic impedance of air

    # Let's try the correct formula
    eta_0_correct = (4 * math.pi ** 2 / speed_of_sound ** 3) * \
                    (driver.F_s ** 3 * driver.V_as / driver.Q_es)

    print(f"\nCorrected formula:")
    print(f"  η₀ = (4π²/c³) × (Fs³Vas/Qes)")
    print(f"  η₀ = {eta_0_correct:.6f}")
    print(f"  This is {eta_0_correct*100:.2f}% efficiency - REASONABLE!")

    # Alternative formula from Beranek (1954)
    # η₀ = (4π²ρ₀/c) × (Fs³Vas/Qes) / Sd²
    # This includes radiation loading

    eta_0_beranek = (4 * math.pi ** 2 * air_density / speed_of_sound) * \
                    (driver.F_s ** 3 * driver.V_as / driver.Q_es) / (driver.S_d ** 2)

    print(f"\nBeranek formula:")
    print(f"  η₀ = (4π²ρ₀/c) × (Fs³Vas/Qes) / Sd²")
    print(f"  η₀ = {eta_0_beranek:.6f}")
    print(f"  This is {eta_0_beranek*100:.2f}% efficiency")

    # Calculate reference SPL using the correct efficiency
    voltage = 2.83  # V
    R_nominal = driver.R_e
    P_ref = (voltage ** 2) / R_nominal
    measurement_distance = 1.0

    p_ref = 20e-6  # Reference pressure: 20 μPa

    print(f"\nReference SPL calculation (with corrected efficiency):")
    print(f"  V = {voltage} V")
    print(f"  R = {R_nominal} Ω")
    print(f"  P_ref = V²/R = {P_ref:.3f} W")

    pressure_rms_wrong = math.sqrt(eta_0_wrong * P_ref * air_density * speed_of_sound /
                                   (4 * math.pi * measurement_distance ** 2))
    spl_ref_wrong = 20 * math.log10(pressure_rms_wrong / p_ref)

    pressure_rms_correct = math.sqrt(eta_0_correct * P_ref * air_density * speed_of_sound /
                                     (4 * math.pi * measurement_distance ** 2))
    spl_ref_correct = 20 * math.log10(pressure_rms_correct / p_ref)

    print(f"\nWith WRONG efficiency ({eta_0_wrong:.6f}):")
    print(f"  p_rms = {pressure_rms_wrong:.3f} Pa")
    print(f"  SPL_ref = {spl_ref_correct:.2f} dB")

    print(f"\nWith CORRECT efficiency ({eta_0_correct:.6f}):")
    print(f"  p_rms = {pressure_rms_correct:.6f} Pa")
    print(f"  SPL_ref = {spl_ref_correct:.2f} dB")

    print(f"\nConclusion:")
    print(f"  The efficiency formula in calculate_spl_ported_transfer_function")
    print(f"  is missing a factor of 1/c² or similar unit conversion.")
    print(f"  It's giving efficiency > 1, which is physically impossible.")


if __name__ == "__main__":
    debug_efficiency()
